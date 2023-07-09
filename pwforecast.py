"""
A Python module to charge/discharge Tesla Powerwall based on solar forecast and peak/off-peak tariffs.

"""

# Author: Tim Hawker

import time
import tzlocal
import datetime
import requests
import pprint
from dateutil import parser


# TODO: Calculate required energy by looking at average historic usage during peak-rate between certain time period.


class PwForecast(object):
    """
    A tool that dynamically sets Powerwall backup reserve percent based on solar forecast.

    PwForecast is useful if you have a day/night rate, and the night rate is long enough
    to charge the batteries.

    PwForecast has primarily been designed for use with 'Self Consumption' mode, although
    it can be used in 'Time Based Control' mode with unpredictable results.

    A Solcast API Key and at least one Site ID will be needed.

    Args:
        teslapy_session (teslapy.Tesla): The tesla session object.
        solcast_api_key (str): The Solcast API Key.
        solcast_site_ids (dict): A dict of Solcast site ID's, where key is the site name
            and value is the site ID.

    Attributes:
        min_reserve_peak_rate (int): The minimum backup reserve to be set when in peak
            grid rates. Default 20.
        min_reserve_off_peak_rate (int): The minimum backup reserve that can be set when
            in off-peak grid rates. Default 30.
        max_reserve (int): The maximum backup reserve that can be set. If you don't like
            charging your batteries to 100%, you can set this value. Default 100.
        timezone (datetime.tzinfo): The tzdata timezone the system sits within. Will use
            timezone from system by default.
        required_energy_peak_rate (int): The amount of energy required during peak rate
            in Wh. When setting peak mode, PwForecast will determine how much solar will
            be generated. It will then calculate how much to fill the batteries based on
            the remaining energy requirement. Default 30000.
        global_retry_limit (int): The number of times the set function should try before
            failing. This is useful if there is a temporary service outage. Be careful
            setting this value too high as solcast has a limited number of API calls.
            Default 5
        global_retry_sleep (int): The time in seconds to sleep before retrying if an
            error occurs. Default 20.
        set_backup_reserve_retry_limit (int): The number of retries to make when setting
            reserve percent. A failure is defined as an unsuccessful switch transition
            by monitoring the power flow, even if the tesla API returns success.
            Default 5.
        set_backup_reserve_response_sleep (int): The time in seconds to sleep before
            testing the current site power flow. This is useful as the Powerwall
            sometimes takes time to respond to requests. Default 20.
        reserve_switch_margin (int): The minimum number of watts to satisfy a successful
            backup reserve power flow transition (e.g. from discharging to charging).
            When setting the backup reserve higher than the current charge, the battery
            needs to be importing more than this value. When setting the backup reserve
            lower than the current charge, the sum of battery+solar needs to be producing
            more than this value. Default 100.
        charge_margin (int): If the Powerwall current charge level is within this margin
            to the value being set, the reserve_switch_margin is not monitored. This is
            necessary because the Powerwall can have unexpected behaviour when setting
            percentages close to current charge percentage. There have been cases where
            the Powerwall has started charging when setting a backup reserve 0.7% less
            than current charge percentage, causing the reserve switch checking logic to
            fail. Default 1.
        full_pack_energy (int): The full pack energy in Wh of a brand new powerwall. This
            is used to calculate the overall state of health of all batteries in the
            system. Default 14000.

    """
    def __init__(self, teslapy_session, solcast_api_key, solcast_site_ids):

        # internal vars
        self._teslapy_session = teslapy_session
        self._solcast_api_key = solcast_api_key
        self._solcast_site_ids = solcast_site_ids

        # basic configuration
        self.min_reserve_peak_rate = 20
        self.min_reserve_off_peak_rate = 30
        self.max_reserve = 100
        self.required_energy_peak_rate = 30000

        # advanced configuration
        self.timezone = tzlocal.get_localzone()
        self.global_retry_limit = 5
        self.global_retry_sleep = 30
        self.set_backup_reserve_retry_limit = 5
        self.set_backup_reserve_response_sleep = 20
        self.reserve_switch_margin = 100
        self.charge_margin = 1
        self.full_pack_energy = 14000

    # solcast
    def get_solar_forecast_tomorrow(self):
        """
        Gets estimated solar production in Wh for tomorrow via Solcast API.

        Returns:
            int: The estimated solar production in Wh for tomorrow.

        """
        # get the estimated production from solcast api
        url = ('https://api.solcast.com.au/rooftop_sites/{site_id}/forecasts?format=json'
               '&api_key={api_key}')
        total_energy_kwh = 0.0
        for solcast_site_name, solcast_site_id in self._solcast_site_ids.items():
            result = requests.get(url.format(site_id=solcast_site_id,
                                             api_key=self._solcast_api_key)).json()

            # get tomorrow start and end dates
            now = datetime.datetime.now(tz=self.timezone)
            today_start = datetime.datetime(year=now.year,
                                            month=now.month,
                                            day=now.day,
                                            tzinfo=self.timezone)
            tomorrow_start = today_start + datetime.timedelta(days=1)
            tomorrow_end = today_start + datetime.timedelta(days=2)

            # get forecast blocks for each time period within sunrise and sunset tomorrow
            forecast_blocks = []
            for forecast_block in result['forecasts']:
                forecast_time = parser.parse(forecast_block['period_end'])
                if tomorrow_start < forecast_time < tomorrow_end:
                    forecast_blocks.append(forecast_block)

            # add each 30 minute block to the total energy value
            site_energy_kwh = 0
            for forecast_block in forecast_blocks:
                site_energy_kwh += forecast_block['pv_estimate'] / 2

            msg = 'Solar forecast tomorrow for {site_name}: {site_energy_kwh:.1f}kWh'
            print(msg.format(site_name=solcast_site_name,
                             site_energy_kwh=site_energy_kwh))
            total_energy_kwh += site_energy_kwh

        msg = 'Solar forecast tomorrow total: {:.1f}kWh'
        print(msg.format(total_energy_kwh))
        return int(total_energy_kwh * 1000)

    # powerwall
    def calculate_backup_reserve(self, forecast_production):
        """
        Calculates a suitable backup reserve percent for the powerwall based on provided
        forecast production.

        Returns:
            int: The charge percentage the powerwall should be charged/discharged to
            based on
        """
        # get the battery, which is a class representing the site
        battery_list = self._teslapy_session.battery_list()
        assert len(battery_list) == 1, 'More than one battery list returned!'
        battery = battery_list[0]

        battery_data = battery.get_battery_data()
        total_pack_energy = battery_data['total_pack_energy']

        available_energy = forecast_production
        charge_percent = self.min_reserve_peak_rate
        pack_energy_increment = total_pack_energy / 100
        while available_energy < self.required_energy_peak_rate:
            available_energy += pack_energy_increment
            charge_percent += 1
            if charge_percent >= self.max_reserve:
                break

        return int(charge_percent)

    def set_backup_reserve_percent(self, percent_target):
        """
        Sets the provided backup reserve percent. If an invalid state is detected after
        setting the reserve percent, the function will retry up to a max number of times
        defined by module level settings.

        An invalid state is defined as charging when it should be discharging, and
        discharging when it should be charging. This seems to happen often, and simply
        sending the command again tends to fix the issue.

        Args:
            percent_target (int): The percent target to set as backup reserve.

        Returns:
            dict: A dictionary containing site status information.

        Raises:
            Exception: If an invalid charge state is detected and the retry limit has
                been reached.

        """
        # cast to int in case a float is provided
        percent_target = int(percent_target)

        # get the battery, which is a class representing the site
        battery_list = self._teslapy_session.battery_list()
        assert len(battery_list) == 1, 'More than one battery list returned!'
        battery = battery_list[0]

        # loop to allow reserve retries
        for index in range(1, self.set_backup_reserve_retry_limit+1):

            # set the battery reserve
            print('Setting backup reserve to {}%, attempt {} of {}'.format(
                percent_target, index, self.set_backup_reserve_retry_limit))
            battery.set_backup_reserve_percent(percent_target)

            # sleep to let the devices update and api sync
            time.sleep(self.set_backup_reserve_response_sleep)

            # check to see if the battery charge/discharge state has correctly changed
            battery_data = battery.get_battery_data()
            msg = 'More than one power reading returned!'
            assert len(battery_data['power_reading']) == 1, msg
            total_pack_energy = battery_data['total_pack_energy']
            battery_count = battery_data['battery_count']
            assert battery_count > 0, 'No batteries detected!'
            pack_soh = (100 / (self.full_pack_energy * battery_count)) * total_pack_energy
            percent_charged = battery_data['percentage_charged']
            power_reading = battery_data['power_reading'][0]
            battery_power = power_reading['battery_power']
            solar_power = power_reading['solar_power']

            # battery within charge margin, set reserve percent and don't check power
            # flow as it can lead to false positives.
            if percent_target-self.charge_margin <= percent_charged <= percent_target+self.charge_margin:
                print('Battery charge within target reserve margin')
                # although the setting is eventually applied, it seems to not change for
                # up to a few hours, and the powerwall can continue draining until it has
                # hit the previous reserve setting. If this is the first iteration, loop
                # again to try and avoid this behaviour.
                if index < 2:
                    msg = ('Reapplying setting to try and ensure powerwall power flow '
                           'behaves as expected.')
                    print(msg)
                else:
                    break

            # battery should be charging
            elif percent_target > percent_charged and battery_power < -self.reserve_switch_margin:
                print('Battery charging at {:.1f}w'.format(battery_power))
                break

            # battery should be discharging, or battery in standby mode and solar
            # providing power
            elif percent_target < percent_charged and battery_power+solar_power > self.reserve_switch_margin:
                print('Battery discharging at {:.1f}w'.format(battery_power))
                # although the setting is eventually applied, it seems to not change for
                # up to a few hours, and the powerwall can continue draining until it has
                # hit the previous reserve setting. If this is the first iteration, loop
                # again to try and avoid this behaviour.
                if index < 2:
                    msg = ('Reapplying setting to try and ensure powerwall will stop '
                           'discharging at set reserve.')
                    print(msg)
                else:
                    break

            else:
                print('Incorrect charge/discharge state')
                pprint.pprint(power_reading)

        # no break
        else:
            pprint.pprint(battery_data)
            raise Exception('Unable to switch battery mode correctly!')

        return {'soc': percent_charged,
                'reserve': percent_target,
                'capacity': total_pack_energy,
                'soh': pack_soh}

    # public
    def set_peak_mode(self):
        """
        Sets backup reserve to 'min_reserve_peak_rate'. Used when transitioning to peak
        rates.

        Attempts to set mode multiple times if an error occurs up to the
        value set in the 'global_retry_limit' attribute.

        Raises:
            Exception: If an invalid charge state is detected and the retry limit has
                been reached.

        """
        for i in range(1, self.global_retry_limit + 1):
            try:
                # status update
                msg = 'Setting peak mode, attempt {i} of {total}'
                print(msg.format(i=i, total=self.global_retry_limit))
                # set the peak reserve
                status = self.set_backup_reserve_percent(self.min_reserve_peak_rate)
                self._print_summary(**status)
            except Exception as e:
                if i == self.global_retry_limit:
                    raise
                msg = '{c}: {e}'
                print(msg.format(c=e.__class__.__name__, e=e))
                # sleep in case of temporary outage
                time.sleep(self.global_retry_sleep)
            else:
                break

    def set_off_peak_mode(self):
        """
        Sets backup reserve based on solar forecast tomorrow. The backup reserve will be
        set between 'min_reserve_off_peak_rate' and 'max_reserve'. Used when
        transitioning to off-peak rates.

        Raises:
            Exception: If an invalid charge state is detected and the retry limit has
            been reached.

        """
        for i in range(1, self.global_retry_limit + 1):
            try:
                # status update
                msg = 'Setting off-peak mode, attempt {i} of {total}'
                print(msg.format(i=i, total=self.global_retry_limit))
                # get the off-peak reserve
                forecast_tomorrow = self.get_solar_forecast_tomorrow()
                charge_percent = self.calculate_backup_reserve(forecast_tomorrow)
                # set the off-peak reserve
                status = self.set_backup_reserve_percent(charge_percent)
                status['solar_forecast'] = forecast_tomorrow
                self._print_summary(**status)
            except Exception as e:
                if i == self.global_retry_limit:
                    raise
                msg = '{c}: {e}'
                print(msg.format(c=e.__class__.__name__, e=e))
                # sleep in case of temporary outage
                time.sleep(self.global_retry_sleep)
            else:
                break

    # internal
    def _print_summary(self, soc, reserve, capacity, soh, solar_forecast=None):
        """
        Prints a status summary of the tesla site, including optional solar forecast.

        Args:
            soc (float): The Powerwall state of charge.
            reserve (float): The Powerwall backup reserve percentage.
            capacity (float): The Powerwall total capacity in Wh.
            soh (float): The Powerwall overall state of health percentage.
            solar_forecast (float): The solar forecast in Wh.

        """
        print('-' * 35)
        if solar_forecast:
            print('Solar forecast tomorrow: {:.1f}kWh'.format(solar_forecast/1000))
        print('Powerwall state of charge: {:.1f}%'.format(soc))
        print('Powerwall backup reserve: {}%'.format(reserve))
        print('Powerwall capacity: {:.2f}kWh'.format(capacity/1000))
        print('Powerwall state of health: {:.1f}%'.format(soh))
        print('-' * 35)
