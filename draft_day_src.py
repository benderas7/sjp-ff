import pandas as pd
import random
import os
import datetime
import pickle
from IPython.display import display, Markdown


# Helper function for bolding text string
def bold(string):
    return '\033[1m' + string + '\033[0m'


# Helper function for ordinals
def ordinal(num):
    lst = ['st', 'nd', 'rd'] + ['th'] * 17 + (
        ['st', 'nd', 'rd'] + ['th'] * 7) * 100
    return str(num) + lst[num - 1]


# Pre-Draft Proceedings

# Helper function - keepers
def determine_keepers(curr_yr, owners, last_yr_df, player_pool):
    keepers_pkl = '{}/keepers.pkl'.format(curr_yr)
    if os.path.exists(keepers_pkl):
        with open(keepers_pkl, 'rb') as f:
            keepers = pickle.load(f)
    else:
        keepers = {}
        for owner in owners:
            input_str = '{}, who would you like to keep? '.format(bold(owner))
            player = input(input_str)
            while True:
                if player == '0':
                    player = None
                    round_lost = None
                    break
                if player in last_yr_df.index:
                    if last_yr_df.Round[player] > 1:
                        round_lost = last_yr_df.Round[player] - 1
                        break
                    else:
                        input_str = '\nYou drafted that player in the 1st ' \
                                    'Round and cannot keep them. Who else ' \
                                    'would you like to keep? '
                        player = input(input_str)
                else:
                    if player in player_pool.index.tolist():
                        round_lost = 16
                        break
                    player = input('\nThat player is not in the player pool. '
                                   'Please re-enter the player, making sure '
                                   'you spelled his name correctly: ')

            if player:
                print('{} will count as your {} pick.\n'.format(
                    bold(player), bold(ordinal(round_lost) + ' Round')))
            keepers[owner] = {'player': player, 'round': round_lost}
        with open(keepers_pkl, 'wb') as f:
            pickle.dump(keepers, f)
    return keepers, player_pool


# Helper function - draft order
def determine_draft_order(curr_yr, owners):
    draft_order_pkl = '{}/draft_order.pkl'.format(curr_yr)
    if os.path.exists(draft_order_pkl):
        with open(draft_order_pkl, 'rb') as f:
            draft_order = pickle.load(f)
    else:
        random.shuffle(owners)
        draft_order = [None] * len(owners)
        for owner in owners:
            input_str = "\n{}, you're up!\nWhich draft slot would you " \
                        "like? ".format(bold(owner))
            slot = int(input(input_str))
            while True:
                if slot > 8 or slot < 1:
                    input_str = '\nSelect a number between 1 and 8: '
                    slot = int(input(input_str))
                elif draft_order[slot - 1]:
                    input_str = '\nThat draft slot is already taken. Pick a ' \
                                'different one: '
                    slot = int(input(input_str))
                else:
                    draft_order[slot - 1] = owner
                    break
        with open(draft_order_pkl, 'wb') as f:
            pickle.dump(draft_order, f)
    return draft_order


# Pre-draft function
def pre_draft():
    # Set parameters
    curr_yr = str(datetime.datetime.now().year)
    last_yr = str(int(curr_yr) - 1)

    # Create folder for current year if need be
    if not os.path.exists(curr_yr):
        os.mkdir(curr_yr)

    # Read last year's Draft Results into Pandas DataFrame
    last_yr_res = '{}/draft_results.xlsx'.format(last_yr)
    last_yr_indv = '{}/indv_draft_results.xlsx'.format(last_yr)
    last_yr_df = pd.read_excel(last_yr_res, index_col=2)

    # Load player pool
    raw_data = '{}/raw_data.xlsx'.format(curr_yr)
    player_pool = pd.read_excel(raw_data, index_col=[0])
    player_pool['Position'] = player_pool['Position'].str.strip()

    # Determine keepers if not already done for current year
    owners = pd.ExcelFile(last_yr_indv).sheet_names
    keepers, player_pool = determine_keepers(
        curr_yr, owners, last_yr_df, player_pool)

    # Determine draft order
    draft_order = determine_draft_order(curr_yr, owners)
    return curr_yr, player_pool, owners, keepers, draft_order


# Draft

# Draft helper function - fill depth chart
def fill_depth_chart(owner, position, depth_charts):
    spots = depth_charts[owner].index.tolist()
    spot = ''
    for spot in spots:
        if position in spot and pd.isnull(
                depth_charts[owner].at[spot, 'Player']):
            return spot
        elif (position == 'RB' or position == 'WR') and spot == 'FLEX' and \
                pd.isnull(depth_charts[owner].at[spot, 'Player']):
            return spot
        elif 'Bench' in spot and pd.isnull(
                depth_charts[owner].at[spot, 'Player']):
            return spot
    return spot[:-1] + str(int(spot[-1]) + 1)


# Draft helper function - keeper management
def manage_keepers(keepers, owners, player_pool, draft_order, draft_history,
                   draft_history_indv, depth_charts):
    for owner, keeper_dct in keepers.items():
        # Extract relevant info from keeper_dct
        player = keeper_dct['player']
        if player:
            round_num = keeper_dct['round']

            the_pick = player_pool.loc[player]

            if round_num % 2:
                spot_in_rd = draft_order.index(owner)
            else:
                spot_in_rd = len(owners) - draft_order.index(owner)
            pick = (round_num - 1) * len(owners) + spot_in_rd

            # Remove keeper from player pool
            player_pool = player_pool.drop(player)

            # Put keepers in draft histories and depth charts
            draft_history.loc[pick] = [str(round_num), player, the_pick[
                'Position'], the_pick['Bye'], the_pick[
                'ESPN Projection'], owner]
            draft_history_indv[owner].loc[pick] = [str(
                round_num), player, the_pick['Position'], the_pick[
                'Bye'], the_pick['ESPN Projection']]
            index = fill_depth_chart(owner, the_pick['Position'], depth_charts)
            depth_charts[owner].loc[index] = [player, the_pick[
                'Bye'], the_pick['ESPN Projection']]
            depth_charts[owner] = depth_charts[owner].astype(
                {'Bye': pd.Int64Dtype()})
    return player_pool, draft_history, draft_history_indv, depth_charts


# Draft function
def draft(curr_yr, player_pool, owners, keepers, draft_order, num_rounds=16):
    # Initialize draft history
    # num_picks = len(draft_order) * num_rounds
    column_names = [
        'Round', 'Player', 'Position', 'Bye', 'ESPN Projection', 'Owner']
    draft_history = pd.DataFrame(index=[], columns=column_names)
    draft_history.index.name = 'Pick Overall'

    # Initialize individual draft histories and depth charts
    draft_history_indv = {}
    depth_charts = {}
    for owner in draft_order:
        column_names = [
            'Round', 'Player', 'Position', 'Bye', 'ESPN Projection']
        draft_history_indv[owner] = pd.DataFrame(
            index=[], columns=column_names)
        draft_history_indv[owner].index.name = 'Pick Overall'
        depth_charts[owner] = pd.read_excel(
            'depth_chart_blank.xlsx', index_col=[0])
    
    # Keeper management
    player_pool, draft_history, draft_history_indv, depth_charts = \
        manage_keepers(keepers, owners, player_pool, draft_order,
                       draft_history, draft_history_indv, depth_charts)
    
    # Perform draft
    results = '{}/draft_results.xlsx'.format(curr_yr)
    indv_results = '{}/indv_draft_results.xlsx'.format(curr_yr)
    indv_depth_charts = '{}/indv_draft_charts.xlsx'.format(curr_yr)

    input_str = """You can either enter who you would like to draft or perform
    any of the following options by entering it's corresponding number:

    1) Look at who you already have drafted
    2) View your current depth chart
    3) See Mike Clay's best players available
    4) See the last 10 players drafted
    5) Look at the full draft history

    """

    draft_params_pkl = '{}/draft_params.pkl'.format(curr_yr)
    if os.path.exists(draft_params_pkl):
        with open(draft_params_pkl, 'rb') as f:
            draft_params = pickle.load(f)
        pick, owner_idx, round_num, player_pool, draft_history, \
            draft_history_indv, depth_charts = draft_params
    else:
        pick = 1
        owner_idx = 0
        round_num = 1

    while round_num < num_rounds + 1:
        print('\n\n\n\n{}'.format(bold('ROUND ' + str(round_num))))
        while owner_idx < len(draft_order):
            if round_num % 2:
                owner = draft_order[owner_idx]
            else:
                owner = draft_order[-1 - owner_idx]

            print("\n\n{}, you're up!".format(bold(owner)))
            while True:
                # Check if keeper should be taken this round
                if keepers[owner]['round'] == round_num:
                    player = keepers[owner]['player']
                    print('\n{} Kept {} with the {} Overall Pick'.format(
                        bold(owner), bold(player), bold(ordinal(pick))))
                    pick += 1
                    owner_idx += 1
                    break

                option = input(input_str)
                if option == '1':
                    display(draft_history_indv[owner].sort_values(
                        'Pick Overall'))
                elif option == '2':
                    display(depth_charts[owner])
                elif option == '3':
                    display(player_pool.head(10))
                elif option == '4':
                    display(draft_history[draft_history.index < pick].tail(10))
                elif option == '5':
                    display(draft_history.sort_values('Pick Overall'))
                else:
                    player = option
                    while True:
                        if option == '9':
                            player = player_pool.head(1).index[0]
                        if player in player_pool.index.tolist():
                            the_pick = player_pool.loc[player]
                            player_pool = player_pool.drop(player)
                            break
                        player = input('\nThat player is not in the player '
                                       'pool. Please re-enter the player, '
                                       'making sure you spelled his name '
                                       'correctly: ')

                    # Update depth chart / draft histories
                    draft_history.loc[pick] = [
                        str(round_num), player, the_pick['Position'], the_pick[
                            'Bye'], the_pick['ESPN Projection'], owner]
                    draft_history_indv[owner].loc[pick] = [
                        str(round_num), player, the_pick['Position'], the_pick[
                            'Bye'], the_pick['ESPN Projection']]
                    index = fill_depth_chart(
                        owner, the_pick['Position'], depth_charts)
                    depth_charts[owner].loc[index] = [
                        player, the_pick['Bye'], the_pick['ESPN Projection']]
                    depth_charts[owner] = depth_charts[owner].astype(
                        {'Bye': pd.Int64Dtype()})

                    # Sort draft histories
                    draft_history = draft_history.sort_values('Pick Overall')
                    for own in owners:
                        draft_history_indv[own] = draft_history_indv[
                            own].sort_values('Pick Overall')

                    # Display pick
                    print('\n{} Took {} with the {} Overall Pick'.format(
                        bold(owner), bold(player), bold(ordinal(pick))))

                    # Save excel spreedsheets
                    writer = pd.ExcelWriter(results)
                    draft_history.to_excel(writer, 'Draft Results')
                    writer.save()

                    writer2 = pd.ExcelWriter(indv_results)
                    for owner, df in draft_history_indv.items():
                        df.to_excel(writer2, owner)
                    writer2.save()

                    writer3 = pd.ExcelWriter(indv_depth_charts)
                    for owner, df in depth_charts.items():
                        df.to_excel(writer3, owner)
                    writer3.save()

                    pick += 1
                    owner_idx += 1

                    # Save draft parameters
                    draft_params = [pick, owner_idx, round_num, player_pool,
                                    draft_history, draft_history_indv,
                                    depth_charts]

                    with open(draft_params_pkl, 'wb') as f:
                        pickle.dump(draft_params, f)

                    break

        round_num += 1
        owner_idx = 0
    return
