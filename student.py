"""Example client."""
import asyncio
import getpass
import json
import os
import websockets
from time import time
from math import sqrt

list_actions = [(1, 0), (-1, 0), (0, 1), (0, -1)]

def node_string(node):
    raw = str().join([str(c) for c in [node[2][y][x] for y in range(node[1]) for x in range(node[1])]])
    grid = node[0]["grid"].split()
    return f"{grid[0]} {raw} {grid[2]}"

def test_win(node):
    last_col = [c[-1] for c in node[2]]
    return "A" in last_col

def car_coordinates(node, char):
    """List coordinates holding a piece."""
    size = node[1]
    map = node[2]
    coordinates = [c for c in [(x, y) for x in range(size) for y in range(size)] if map[c[1]][c[0]] == char]
    return coordinates

def move(node, piece, direction):
    """Move piece in direction given by a vector."""
    car_coord = car_coordinates(node, piece)
    grid_side = node[1]

    if direction[0] and car_coord[0][1] != car_coord[1][1]:
        return None
    if direction[1] and car_coord[0][0] != car_coord[1][0]:
        return None

    new_map = node[2]

    if direction[0] == 1:
        if car_coord[-1][0] < grid_side-1 and new_map[car_coord[-1][1]][car_coord[-1][0] + 1] == 'o':
            new_map[car_coord[0][1]][car_coord[0][0]] = 'o'
            new_map[car_coord[-1][1]][car_coord[-1][0] + 1] = piece
    elif direction[0] == -1:
        if car_coord[0][0] > 0 and new_map[car_coord[0][1]][car_coord[0][0] - 1] == 'o':
            new_map[car_coord[0][1]][car_coord[0][0] - 1] = piece
            new_map[car_coord[-1][1]][car_coord[-1][0]] = 'o'
    elif direction[1] == 1:
        if car_coord[-1][1] < grid_side-1 and new_map[car_coord[-1][1] + 1][car_coord[-1][0]] == 'o':
            new_map[car_coord[0][1]][car_coord[0][0]] = 'o'
            new_map[car_coord[-1][1] + 1][car_coord[-1][0]] = piece
    elif direction[1] == -1:
        if car_coord[0][1] > 0 and new_map[car_coord[0][1] - 1][car_coord[0][0]] == 'o':
            new_map[car_coord[0][1] - 1][car_coord[0][0]] = piece
            new_map[car_coord[-1][1]][car_coord[-1][0]] = 'o'

    return new_map

def create_node(state, parent, depth, action, heuristic=0):
    grid = state["grid"].split()[1]
    grid_side = int(sqrt(len(grid)))
    map = [list(grid[y:x]) for y, x in ((i * grid_side, (i + 1) * grid_side) for i in range(grid_side))]
    return state, grid_side, map, parent, depth, action, heuristic


class GameTree:
    """Classe que representa a árvore de busca do jogo.\n\n
       root: o node raiz\n
       state: o string que é dado pelo servidor\n
       all_nodes: uma lista com todos os nodes da árvore\n
       solution: o node que representa a solução\n
       open_nodes: uma lista com os nodes que ainda não foram expandidos\n
       pieces: uma lista com as peças(leia-se carros) do jogo\n"""


    def __init__(self, state):
        self.root = create_node(state, None, 0, None)
        self.state = state
        self.all_nodes = [self.root]
        self.solution = []
        self.open_nodes = [0] 
        self.pieces = self.get_pieces()
        self.all_states = []


    def get_pieces(self):
        """Retorna uma lista com as peças do jogo.\n\n
        Verifica todos as células do mapa cujo valor é uma letra maiúscula entre 'A' e 'P', 
        que é o range de letras que é usado para representar as peças do jogo no ficheiro 
        levels.txt.\n"""
        pieces = [c for c in self.state["grid"] if c.isupper()]
        return list(set(pieces))


    def get_path(self, node):
        """Retorna uma lista com os ids dos nodes que estão no caminho da solução."""
        if node[3] is None:
            return []
        nodes = self.get_path(self.all_nodes[node[3]])
        return nodes + [node[3]]


    def search(self):
        """Método que preenche a árvore de busca até encontrar uma solução.\n
           Depois retorna a lista de teclas deduzida da lista das ações que levam à solução."""
        while self.open_nodes:
            nodeID = self.open_nodes.pop(0)
            node = self.all_nodes[nodeID]

            lnewnodes = []

            for a, new_map in self.possible_actions(node):
                new_state = node[0].copy()
                new_state["grid"] = node_string(new_map)
                new_state["cursor"] = a[3][0:2]
                new_state["selected"] = a[0]

                for i in range(node[1]):
                    if 'A' in new_map[2][i]:
                        row = i
                        break

                heuristic = [new_map[2][row][c] != 'o' for c in range(node[1])].count(True)

                new_node = create_node(new_state, nodeID, node[4] + 1, a, heuristic)
                if new_state["grid"] not in self.all_states:
                    self.all_states.append(new_state["grid"])
                    lnewnodes.append(len(self.all_nodes))
                    self.all_nodes.append(new_node)

            self.open_nodes.extend(lnewnodes)
            self.open_nodes.sort(key=lambda x: self.all_nodes[x][6])

            for n in lnewnodes:
                if test_win(self.all_nodes[n]):
                    node_list = self.get_path(self.all_nodes[n])
                    node_list.append(n)

                    self.solution = [self.all_nodes[node_list[i]] for i in range(len(node_list))]

                    return self.get_keys(self.solution)

        return None


    def get_keys(self, node_list):
        """Itera sobre a lista de nodes e retorna uma lista com as teclas deduzidas"""
        key_presses = []
        while len(node_list) > 1:
            n = node_list[0]
            key_presses += (self.action_to_keys(node_list[1][5], n))
            node_list.pop(0)

        if len(key_presses) == 0:
            self.search()

        return key_presses

    def action_to_keys(self, action, node):
        """Executa a ação que leva um node pai a um node filho e retorna uma lista com as teclas deduzidas"""
        keys = []

        if node[0]["selected"] not in [action[0], ""]: keys.append(" ")
        keys += (self.move_keys(action[1], action[2]))
        if node[0]["selected"] != action[0]: keys.append(" ")
        keys += (self.move_keys(action[2], action[3]))

        return keys


    def move_keys(self, ci, cf):
        """Retorna uma lista com as teclas deduzidas para mover uma peça de ci (coordenada inicial) para cf (coordenada final)"""
        keys = []

        if ci[0] < cf[0]:
            keys += ([*("d" * (cf[0] - ci[0]))])
        else:
            keys += ([*("a" * (ci[0] - cf[0]))])
        if ci[1] > cf[1]:
            keys += ([*("w" * (ci[1] - cf[1]))])
        else:
            keys += ([*("s" * (cf[1] - ci[1]))])

        return keys


    def possible_actions(self, node):
        """Deduz e retorna todas as acções possíveis de um dado node"""
        list_action_map = []

        for p in self.pieces:
            for a in list_actions:
                node_copy = create_node(node[0], node[3], node[4] + 1, a)
                coord_c = node[0].get("cursor")
                coord_i = car_coordinates(node_copy, p)
                move(node_copy, p, a)
                if node_copy is not None:
                    coord_f = car_coordinates(node_copy, p)
                    if node[3] is not None:
                        coord_c = node[5][3]
                    action = (p, coord_c, coord_i[0], coord_f[0])
                    list_action_map.append((action, node_copy))
                    if node[2][car_coordinates(node, "A")[-1][0]][car_coordinates(node, "A")[-1][1]:] == ["o" for i in range(len(node[2][car_coordinates(node, "A")[-1][1]:]))]:
                        list_action_map = [(action, node_copy)]
                        return list_action_map
        return list_action_map



async def agent_loop(server_address="localhost:8000", agent_name="98586"):
    """Example client loop."""
    async with websockets.connect(f"ws://{server_address}/player") as websocket:
        # Lista que vai conter as jogadas que o agente decide
        key_presses = []
        # Receive information about static game properties
        await websocket.send(json.dumps({"cmd": "join", "name": agent_name}))

        while True:
            try:
                state = json.loads(
                    await websocket.recv()
                )  # receive game update, this must be called timely or your game will get out of sync with the server

                # Se a lista de teclas a serem enviadas estiver vazia, o agente deve decidir as teclas a serem enviadas
                if len(key_presses) == 0:
                    tree = GameTree(state)
                    key_presses = tree.search()

                if key_presses is None:
                    key_presses = []
                    continue

                start = time()

                while len(key_presses) > 0:

                    key = key_presses[0]

                    await websocket.send(
                        json.dumps({"cmd": "key", "key": key})
                    )  # send key command to server

                    new_state = json.loads(await websocket.recv())

                    if time() - start > 0.2:
                        key_presses = []
                        break

                    if state["cursor"] != new_state["cursor"] or state["selected"] != new_state["selected"]:
                        key_presses.pop(0)
                        break

            except websockets.exceptions.ConnectionClosedOK:
                print("Server has cleanly disconnected us")
                return


# DO NOT CHANGE THE LINES BELLOW
# You can change the default values using the command line, example:
# $ NAME='arrumador' python3 client.py
loop = asyncio.get_event_loop()
SERVER = os.environ.get("SERVER", "localhost")
PORT = os.environ.get("PORT", "8000")
NAME = os.environ.get("NAME", getpass.getuser())
loop.run_until_complete(agent_loop(f"{SERVER}:{PORT}", NAME))