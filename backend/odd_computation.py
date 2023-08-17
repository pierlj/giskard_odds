import argparse
import os
import networkx as nx
import itertools
from collections import defaultdict
import logging

from utils import *


def compute_path_length(path, universe_graph, autonomy):
    path_edge_weights = [universe_graph[path[i]][path[i+1]]['weight'] for i in range(len(path) - 1)]
    total_length = 0
    length_without_refuel = 0
    current_length_before_refuel = 0
    for w in path_edge_weights:
        total_length += w
        current_length_before_refuel += w
        length_without_refuel += w
        if current_length_before_refuel >= autonomy:
            current_length_before_refuel = 0
            total_length += 1

    return total_length, length_without_refuel

def compute_path_odds(path, universe_graph, empire_dict, millenium_dict):
    autonomy = millenium_dict['autonomy']

    bounty_dict = defaultdict(set)
    for bounty in empire_dict['bounty_hunters']:
        bounty_dict[bounty['planet']].add(bounty['day'])

    path_edge_weights = [universe_graph[path[i]][path[i+1]]['weight'] for i in range(len(path) - 1)]
    total_length = 0
    length_without_refuel = sum(path_edge_weights)
    n_refuel = length_without_refuel // autonomy
    total_length = n_refuel + length_without_refuel # minimum total length 

    # where to refuel and where to stop 
    if total_length > int(empire_dict['countdown']):
        return 0, None 
    fuel = autonomy
    
    # split planets into two groups:
    # 1 - where the spacecraft must refuel, i.e. planets where incoming and outgoing travels are above the falcon autonomy
    # 2 - the others planets

    forced_refuel = []
    may_stop_or_refuel = [path[0]]
    for i in range(1, len(path) - 1):
        incoming_w = universe_graph[path[i-1]][path[i]]['weight']
        outgoing_w = universe_graph[path[i]][path[i+1]]['weight']
        if (incoming_w + outgoing_w) > autonomy:
            forced_refuel.append(path[i])
        
        may_stop_or_refuel.append(path[i])
    
    allowed_stop_or_refuel = empire_dict['countdown'] - length_without_refuel - len(forced_refuel) #- total_length #+ len(forced_refuel)

    itinerary_dates = []
    best_stops = None

    if allowed_stop_or_refuel > 0:
        lowest_encounter = empire_dict['countdown']
        for stops in itertools.combinations_with_replacement(may_stop_or_refuel, allowed_stop_or_refuel):
            stops = list(stops) + forced_refuel
            itinerary_dates = []
            stops_per_planet = {planet: stops.count(planet) for planet in path}
            

            for idx_planet, planet in enumerate(path):
                if idx_planet == 0:
                    itinerary_dates.append((0,stops_per_planet[planet]))
                else:
                    arrival_day = itinerary_dates[-1][-1] + path_edge_weights[idx_planet - 1]
                    leaving_day = arrival_day + stops_per_planet[planet]
                    itinerary_dates.append((arrival_day, leaving_day))

            nb_encounters = compute_encounters(path, itinerary_dates, bounty_dict)

            if nb_encounters < lowest_encounter:
                lowest_encounter = nb_encounters
                best_stops = itinerary_dates.copy()
    else:
        for idx_planet, planet in enumerate(path):
            if idx_planet == 0:
                itinerary_dates.append((0,0))
            else:
                arrival_day = itinerary_dates[-1][-1] + path_edge_weights[idx_planet - 1]
                leaving_day = arrival_day
                if planet in forced_refuel:
                    leaving_day += 1

                itinerary_dates.append((arrival_day, leaving_day))
        lowest_encounter = compute_encounters(path, itinerary_dates, bounty_dict)
        best_stops = itinerary_dates.copy()
    odds = (1 - sum(9 **i / (10 ** (i+1)) for i in range(lowest_encounter))) * 100
    return odds, best_stops          
        
       
def compute_encounters(path, itinerary_dates, bounty_presence):
    itinerary_dates
    falcon_presence = {}
    day = 0
    for planet, (arrival, departure) in zip(path, itinerary_dates):
        falcon_presence[planet] = set(i for i in range(arrival, departure + 1))
        day = departure + 1

    bounty_planets = set(bounty_presence) 
    falcon_planets = set(falcon_presence)

    encounters = 0
    for planet in bounty_planets.intersection(falcon_planets):
        encounters += len(bounty_presence[planet].intersection(falcon_presence[planet]))

    return encounters

def compute_odds(millenium_path, empire_path):
    millenium_dict, empire_dict = get_json_contents(millenium_path, empire_path)
    if millenium_dict is None or empire_dict is None:
        logger.warn(' Abort Mission !')
        return None, None

    # check weither route_db is absolute or relative path
    if os.path.isfile(millenium_dict['routes_db']):
        db_path = millenium_dict['routes_db']
    else:
        db_directory = os.path.dirname(millenium_path)
        db_path = os.path.join(db_directory, millenium_dict['routes_db'])
    universe_graph = build_unvierse_graph(db_path, millenium_dict)
    
    try:
        shortest_path = nx.algorithms.shortest_path(universe_graph, 
                                                source=millenium_dict['departure'], 
                                                target=millenium_dict['arrival'], 
                                                weight='weight')
        
    except nx.NetworkXNoPath:
        logger.info(' No path found between {} and {}. Its odds of success are 0%.'.format(millenium_dict['departure'], 
                                                                 millenium_dict['arrival']))
        return 0, None    
    
    path_length, path_length_without_refuel = compute_path_length(shortest_path, 
                                      universe_graph, 
                                      millenium_dict['autonomy'])

    if path_length > int(empire_dict['countdown']):
        logger.info(' Shortest path is too slow for the Falcon to reach {} before the Death Star annihilates the planet... Its odds of success are 0%.'.format(millenium_dict['arrival']))
        return 0, None
    odds = compute_path_odds(shortest_path, universe_graph, empire_dict, millenium_dict)

    max_odds = 0
    best_itinerary = None
    best_path = None
    for path in nx.shortest_simple_paths(universe_graph, millenium_dict['departure'], millenium_dict['arrival'], weight='weight'):
        odds, itinerary = compute_path_odds(path, universe_graph, empire_dict, millenium_dict)
        if odds > max_odds:
            max_odds = odds
            best_itinerary = itinerary
            best_path = path
        max_odds = max(odds, max_odds)

    logger.info(' The Falcon can reach {} before the Death Star annihilates the planet! Its odds of success are {}%.'.format(millenium_dict['arrival'], max_odds))
    return max_odds, prettify_path(best_path, best_itinerary)                                          


def parse_command_line():
    parser = argparse.ArgumentParser('parser', add_help=True)

    parser.add_argument('millenium_path', default='', type=str, help="Path to the Millenium Falcon config file")
    parser.add_argument('empire_path', default='', type=str, help="Path to the Empire config file")
    parser.add_argument('--verbose', help="Display logs", action=argparse.BooleanOptionalAction)

    return parser.parse_args()

if __name__ == '__main__':
    args = parse_command_line()
    logging.basicConfig(level=logging.INFO if args.verbose else logging.CRITICAL) 
    odds, itinerary = compute_odds(args.millenium_path, args.empire_path)
    if odds is not None:
        print('The odds of success are {:.1f}%.'.format(odds))