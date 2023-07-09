## PwForecast

A Python module to charge/discharge Tesla Powerwall based on solar forecast and peak/off-peak tariffs. 

Utilises the excellent [TeslaPy](https://github.com/tdorssers/TeslaPy) by Tim Dorssers.

PwForecast is primarily designed for those with dual rate tariffs. If there is interest in expanding this to provide
more flexible control for those with more complex tariffs, please let me know.

[![Version](https://img.shields.io/pypi/v/pwforecast)](https://pypi.org/project/pwforecast)


## Getting Started

PwForecast requires a Solcast API key and Site ID. You can sign up for a 
[free Hobbyist account](https://toolkit.solcast.com.au/register) which allows up to two sites and 50 API calls per day. 

[TeslaPy](https://github.com/tdorssers/TeslaPy) has great documentation on getting started. It even works with two-factor
authentication enabled.

Rather than inherit, PwForecast requires an instance of a [TeslaPy](https://github.com/tdorssers/TeslaPy) Tesla class 
passed to it. This allows you to configure the object based on your credentials before passing to PwForecast.  

When using PwForecast, Self Powered mode is recommended. Time Based Control could be used if you need to charge
faster than 1.7kW per Powerwall, but results may be unpredictable. 


## Overview 

PwForecast has two main methods, `set_peak_mode` and `set_off_peak_mode`. Both can be configured using a PwForecast
instance. 

Here is an example showing how to configure teslapy and PwForecast:

```python
import teslapy
from pwforecast import PwForecast

tesla_email = 'name@example.com'
solcast_api_key = '1234-1234'
solcast_site_ids = {'Site_A': '1234-1234',
                    'Site_B': '1234-1234'}

with teslapy.Tesla(email=tesla_email) as tesla:

    pw_forecast = PwForecast(teslapy_session=tesla,
                             solcast_api_key=solcast_api_key,
                             solcast_site_ids=solcast_site_ids)
```


## Setting Peak Mode

Use this method when your peak rate starts. You can configure what backup reserve the Powerwall can discharge down
to by setting the `min_reserve_peak_rate` value.

```python
pw_forecast.min_reserve_peak_rate = 10  # Default 20
pw_forecast.set_peak_mode()
```

PwForecast will try to ensure power flow behaves as expected. Please see [Retry Logic](#retry-logic) for more info. 

A summary report will then be printed:
```text
-----------------------------------
Powerwall state of charge: 19.7%
Powerwall backup reserve: 100%
Powerwall capacity: 26.59kWh
Powerwall state of health: 95.0%
-----------------------------------
```


## Setting Off-Peak Mode

Use this method when your off-peak rate starts. This requires a little more setup.
 * Configure what backup reserve the Powerwall can discharge down to by setting the `min_reserve_off_peak_rate` attribute.
 * Configure the maximum backup reserve allowed by setting the `max_reserve` attribute. 
 * Configure the amount of energy you require during the peak-rate by setting the `required_energy_peak_rate` attribute.

When setting peak mode, PwForecast will determine how much solar will be generated tomorrow. It will then calculate how 
much to fill the batteries based on the remaining energy requirement that solar will not satisfy. If solar generation
completely satisfies `required_energy_peak_rate`, the backup reserve will be set to `min_reserve_off_peak_rate`. 

`get_solar_forecast_tomorrow` is called internally as part of `set_off_peak_mode`. This will consume a Solcast API call 
per site ID you have provided. 

```python
pw_forecast.min_reserve_off_peak_rate = 25  # Default 30
pw_forecast.max_reserve = 95  # Default 100
pw_forecast.required_energy_peak_rate = 20000  # Default 30000
pw_forecast.set_off_peak_mode()
```

PwForecast will try to ensure power flow behaves as expected. Please see [Retry Logic](#retry-logic) for more info. 

A summary report will then be printed:
```text
-----------------------------------
Solar forecast tomorrow: 10.2kWh
Powerwall state of charge: 19.7%
Powerwall backup reserve: 100%
Powerwall capacity: 26.59kWh
Powerwall state of health: 95.0%
-----------------------------------
```


## Getting Solar Forecast

If you're only interested in getting the solar forecast, you can call `get_solar_forecast_tomorrow`. This will
consume a Solcast API call per site ID you have provided. The value returned will be an int of the estimated
solar forecast tomorrow in Wh.

```python
pw_forecast.get_solar_forecast_tomorrow()
```


## Retry Logic

When setting backup reserve, it is common to take two or three attempts before power flow changes to the expected 
figures. As the Tesla API is unofficial, it is difficult to determine why. Waiting longer does not seem to fix this 
issue, although waiting upwards of 45 minutes does sometimes result in power flow eventually changing correctly. 
Re-applying the setting does appear to fix this issue. Perhaps the unofficial Tesla API is missing a commit command. 
Please do let me know if you have any ideas. 

Calling `set_peak_mode` and `set_off_peak_mode` will set the backup reserve, wait 20 seconds, and then check site 
power flow to confirm the setting has been applied. If an incorrect power flow is detected, the method will retry 
up to the `set_backup_reserve_retry_limit` limit. If the `set_backup_reserve_retry_limit` is reached, an exception 
will be raised and caught by the global retry logic. PwForecast will then attempt to re-apply the setting up to the 
`global_retry_limit` limit, eventually raising an exception. 

Both `set_backup_reserve_retry_limit` and `global_retry_limit` can be configured on the PwForecast instance. The 
`set_backup_reserve_retry_limit` has been split from the `global_retry_limit` to try and avoid exhausting Solcast API calls. 

The amount of time between each `global_retry` can be configured via `global_retry_sleep`. The amount of time 
between each `set_backup_reserve_retry_limit` can be configured via `set_backup_reserve_response_sleep`.


## Advanced Configuration

PwForecast has a few advanced configuration options. Please check the class docstring for more info. 

