import pandas as pd
import numpy as np
import random
import os
import datetime
import pickle
from IPython.display import display


# Helper function for bolding text string
def bold(string):
    return '\033[1m' + string + '\033[0m'


# Helper function for ordinals
def ordinal(num):
    lst = ['st', 'nd', 'rd'] + ['th'] * 17 + (
        ['st', 'nd', 'rd'] + ['th'] * 7) * 100
    return str(num) + lst[num - 1]


class Draft:

    def __init__(self, draft_format):
        # Draft basics
        assert draft_format in ('Salary Cap', 'Snake')
        self.format = draft_format
        self.curr_yr = str(datetime.datetime.now().year)
        self.last_yr = str(int(self.curr_yr) - 1)
        self.num_rounds = 16
        if self.format == 'Snake':
            self.input_str = """
            You can either enter who you would like to draft or perform any of 
            the following options by entering it's corresponding number:
    
            1) Look at who you already have drafted
            2) View your current depth chart
            3) See Mike Clay's best players available
            4) See the last 10 players drafted
            5) Look at the full draft history
    
            """
        else:
            self.input_str = """
            You can either enter who you would like to nominate for the 
            auction or perform any of the following options by entering it's 
            corresponding number:

            1) Look at individual draft histories
            2) View all current depth charts
            3) See expected salaries and point projections
            4) See the last 10 players drafted
            5) Look at the full draft history
            6) Check how much a player is worth

            """

        # File paths
        self.keepers_pkl = '{}/keepers.pkl'.format(self.curr_yr)
        self.draft_order_pkl = '{}/draft_order.pkl'.format(self.curr_yr)
        self.last_yr_res = '{}/draft_results.xlsx'.format(self.last_yr)
        self.raw_data = '{}/raw_data.xlsx'.format(self.curr_yr)
        self.last_yr_indv = '{}/indv_draft_results.xlsx'.format(self.last_yr)
        self.results = '{}/draft_results.xlsx'.format(self.curr_yr)
        self.indv_results = '{}/indv_draft_results.xlsx'.format(self.curr_yr)
        self.indv_depth_charts = '{}/indv_depth_charts.xlsx'.format(
            self.curr_yr)
        self.draft_params_pkl = '{}/draft_params.pkl'.format(self.curr_yr)

        # Data structures
        self.owners = pd.ExcelFile(self.last_yr_indv).sheet_names
        self.last_yr_df = pd.read_excel(self.last_yr_res, index_col=2)
        self.player_pool = pd.read_excel(self.raw_data, index_col=[0])
        self.player_pool['Position'] = self.player_pool['Position'].str.strip()
        if os.path.exists(self.keepers_pkl):
            with open(self.keepers_pkl, 'rb') as f:
                self.keepers = pickle.load(f)
        else:
            self.keepers = None
        if os.path.exists(self.draft_order_pkl):
            with open(self.draft_order_pkl, 'rb') as f:
                self.draft_order = pickle.load(f)
        else:
            self.draft_order = None
        if self.format == 'Snake':
            column_names = ['Round', 'Player', 'Position', 'Bye',
                            'ESPN Projection', 'Owner']
        else:
            column_names = ['Salary', 'Player', 'Position', 'Bye',
                            'ESPN Projection', 'Owner']
        self.draft_history = pd.DataFrame(index=[], columns=column_names)
        self.draft_history.index.name = 'Pick Overall'
        self.draft_history_indv = {}
        self.depth_charts = {}
        for owner in self.owners:
            self.draft_history_indv[owner] = pd.DataFrame(
                index=[], columns=column_names[:-1])
            self.draft_history_indv[owner].index.name = 'Pick Overall'
            self.depth_charts[owner] = pd.read_excel(
                'depth_chart_blank.xlsx', index_col=[0])

        # Draft trackers
        self.pick = 1
        self.owner_idx = 0
        self.round_num = 1

        # Resume draft if previously started
        if os.path.exists(self.draft_params_pkl):
            with open(self.draft_params_pkl, 'rb') as f:
                draft_params = pickle.load(f)
            self.pick, self.owner_idx, self.round_num, self.player_pool, \
                self.draft_history, self.draft_history_indv, \
                self.depth_charts = draft_params

    def _determine_keepers(self):
        self.keepers = {}
        for owner in self.owners:
            input_str = '{}, who would you like to keep? '.format(bold(owner))
            player = input(input_str)
            while True:
                if player == '0':
                    player = None
                    round_lost = None
                    break
                if player in self.last_yr_df.index:
                    if self.last_yr_df.Round[player] > 1:
                        round_lost = self.last_yr_df.Round[player] - 1
                        break
                    else:
                        input_str = '\nYou drafted that player in the 1st ' \
                                    'Round and cannot keep them. Who else ' \
                                    'would you like to keep? '
                        player = input(input_str)
                else:
                    if player in self.player_pool.index.tolist():
                        round_lost = 16
                        break
                    player = input('\nThat player is not in the player pool. '
                                   'Please re-enter the player, making sure '
                                   'you spelled his name correctly: ')

            if player:
                if self.format == 'Snake:':
                    print('{} will count as your {} pick.\n'.format(
                        bold(player), bold(ordinal(round_lost) + ' Round')))
                    self.keepers[owner] = {
                        'player': player, 'round': round_lost}
                elif self.format == 'Salary Cap':
                    print('You have elected to keep {}.\n'.format(
                        bold(player)))
                    self.keepers[owner] = {'player': player, 'round': 0}
        with open(self.keepers_pkl, 'wb') as f:
            pickle.dump(self.keepers, f)

    def _determine_draft_order(self):
        random.shuffle(self.owners)
        self.draft_order = [None] * len(self.owners)
        for owner in self.owners:
            input_str = "\n{}, you're up!\nWhich draft slot would you " \
                        "like? ".format(bold(owner))
            slot = int(input(input_str))
            while True:
                if slot > 8 or slot < 1:
                    input_str = '\nSelect a number between 1 and 8: '
                    slot = int(input(input_str))
                elif self.draft_order[slot - 1]:
                    input_str = '\nThat draft slot is already taken. ' \
                                'Pick a different one: '
                    slot = int(input(input_str))
                else:
                    self.draft_order[slot - 1] = owner
                    break
        with open(self.draft_order_pkl, 'wb') as f:
            pickle.dump(self.draft_order, f)

    @staticmethod
    def _fill_depth_chart(owner, position, depth_charts):
        spots = depth_charts[owner].index.tolist()
        spot = ''
        for spot in spots:
            if position in spot and pd.isnull(
                    depth_charts[owner].at[spot, 'Player']):
                return spot
            elif (position == 'RB' or position == 'WR') and spot == \
                    'FLEX' and pd.isnull(depth_charts[owner].at[
                                             spot, 'Player']):
                return spot
            elif 'Bench' in spot and pd.isnull(
                    depth_charts[owner].at[spot, 'Player']):
                return spot
        return spot[:-1] + str(int(spot[-1]) + 1)

    def _update_data_structs(self, player, the_pick, owner):
        # Update depth chart / draft histories
        self.draft_history.loc[self.pick] = [
            str(self.round_num), player, the_pick['Position'], the_pick[
                'Bye'], the_pick['ESPN Projection'], owner]
        self.draft_history_indv[owner].loc[self.pick] = [
            str(self.round_num), player, the_pick['Position'], the_pick[
                'Bye'], the_pick['ESPN Projection']]
        index = self._fill_depth_chart(
            owner, the_pick['Position'], self.depth_charts)
        self.depth_charts[owner].loc[index] = [
            player, the_pick['Bye'], the_pick['ESPN Projection']]
        self.depth_charts[owner] = self.depth_charts[
            owner].astype({'Bye': pd.Int64Dtype()})

        # Sort draft histories
        self.draft_history = self.draft_history.sort_values(
            'Pick Overall')
        for own in self.owners:
            self.draft_history_indv[own] = \
                self.draft_history_indv[own].sort_values(
                    'Pick Overall')

    def _save_data(self):
        # Save excel spreedsheets
        writer = pd.ExcelWriter(self.results)
        self.draft_history.to_excel(writer, 'Draft Results')
        writer.save()

        writer2 = pd.ExcelWriter(self.indv_results)
        for owner, df in self.draft_history_indv.items():
            df.to_excel(writer2, owner)
        writer2.save()

        writer3 = pd.ExcelWriter(self.indv_depth_charts)
        for owner, df in self.depth_charts.items():
            df.to_excel(writer3, owner)
        writer3.save()

        # Save draft parameters
        draft_params = [self.pick + 1, self.owner_idx + 1, self.round_num,
                        self.player_pool, self.draft_history,
                        self.draft_history_indv, self.depth_charts]

        with open(self.draft_params_pkl, 'wb') as f:
            pickle.dump(draft_params, f)

    def _manage_keepers(self):
        for owner, keeper_dct in self.keepers.items():
            # Extract relevant info from keeper_dct
            player = keeper_dct['player']
            if player:
                round_num = keeper_dct['round']

                the_pick = self.player_pool.loc[player]

                if round_num % 2:
                    spot_in_rd = self.draft_order.index(owner)
                else:
                    spot_in_rd = len(self.owners) - self.draft_order.index(
                        owner)
                self.pick = (round_num - 1) * len(self.owners) + spot_in_rd

                # Remove keeper from player pool
                self.player_pool = self.player_pool.drop(player)

                # Put keeper in draft histories and depth charts
                self._update_data_structs(player, the_pick, owner)
                self._save_data()

    def pre_draft(self):
        # Create folder for current year if need be
        if not os.path.exists(self.curr_yr):
            os.mkdir(self.curr_yr)

        # Determine keepers if not already done for current year
        if self.keepers is None:
            self._determine_keepers()

        # Determine draft order
        if self.draft_order is None:
            self._determine_draft_order()

        # Keeper management
        if not os.path.exists(self.draft_params_pkl):
            self._manage_keepers()

    def _one_pick_snake(self, owner):
        # Notify owner they are up
        print("\n\n{}, you're on the clock!".format(bold(owner)))

        # Check if keeper should be taken this round
        if self.keepers[owner]['round'] == self.round_num:
            player = self.keepers[owner]['player']
            print('\n{} Kept {} with the {} Overall Pick'.format(
                bold(owner), bold(player), bold(ordinal(self.pick))))
            return

        while True:
            option = input(self.input_str)
            if option == '1':
                all_indv_draft_histories = pd.concat(
                    self.draft_history_indv.values(),
                    keys=self.draft_history_indv.keys())
                display(all_indv_draft_histories)
            elif option == '2':
                all_depth_charts = pd.concat(
                    self.depth_charts, axis=1).replace(np.nan, '', regex=True)
                mid_index = len(self.owners) * 3 // 2
                display(all_depth_charts.iloc[:, :mid_index])
                display(all_depth_charts.iloc[:, mid_index:])
            elif option == '3':
                display(self.player_pool.head(10))
            elif option == '4':
                display(self.draft_history[
                            self.draft_history.index < self.pick].tail(10))
            elif option == '5':
                display(self.draft_history.sort_values('Pick Overall'))
            elif option == '6':
                check = input('Enter the player you would like to check the '
                              'salary of: ')
                if check in self.player_pool.index:
                    display(self.player_pool.loc[check])
                else:
                    print('\nThat player is not in the player pool.')
            else:
                player = option
                while True:
                    if option == '9':
                        player = self.player_pool.head(1).index[0]
                    if player in self.player_pool.index.tolist():
                        the_pick = self.player_pool.loc[player]
                        self.player_pool = self.player_pool.drop(
                            player)
                        break
                    player = input('\nThat player is not in the player pool. '
                                   'Please re-enter the player, making sure '
                                   'you spelled his name correctly: ')

                # Display pick
                print('\n{} Took {} with the {} Overall Pick'.format(
                    bold(owner), bold(player), bold(ordinal(self.pick))))

                # Put player in draft histories and depth charts
                self._update_data_structs(player, the_pick, owner)
                self._save_data()
                return

    def _one_pick_salary_cap(self, owner):
        # Notify owner they are up
        print("\n\n{}, you're up to nominate!".format(bold(owner)))

        while True:
            option = input(self.input_str)
            if option == '1':
                display(self.draft_history_indv[owner].sort_values(
                    'Pick Overall'))
            elif option == '2':
                display(self.depth_charts[owner])
            elif option == '3':
                display(self.player_pool.head(10))
            elif option == '4':
                display(self.draft_history[
                            self.draft_history.index < self.pick].tail(10))
            elif option == '5':
                display(self.draft_history.sort_values('Pick Overall'))
            else:
                player = option
                while True:
                    if option == '9':
                        player = self.player_pool.head(1).index[0]
                    if player in self.player_pool.index.tolist():
                        the_pick = self.player_pool.loc[player]
                        self.player_pool = self.player_pool.drop(
                            player)
                        break
                    player = input('\nThat player is not in the player pool. '
                                   'Please re-enter the player, making sure '
                                   'you spelled his name correctly: ')

                # Display pick
                print('\n{} Took {} with the {} Overall Pick'.format(
                    bold(owner), bold(player), bold(ordinal(self.pick))))

                # Put player in draft histories and depth charts
                self._update_data_structs(player, the_pick, owner)
                self._save_data()
                return

    def draft(self):
        # Perform draft
        while self.round_num < self.num_rounds + 1:
            print('\n\n\n\n{}'.format(bold('ROUND ' + str(self.round_num))))
            while self.owner_idx < len(self.draft_order):
                if self.round_num % 2:
                    curr_owner = self.draft_order[self.owner_idx]
                else:
                    curr_owner = self.draft_order[-1 - self.owner_idx]

                if self.format == 'Snake':
                    self._one_pick_snake(curr_owner)
                elif self.format == 'Salary Cap':
                    self._one_pick_salary_cap(curr_owner)

                self.pick += 1
                self.owner_idx += 1

            self.round_num += 1
            self.owner_idx = 0
        return
