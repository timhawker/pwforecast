## PwForecast

A Python module to charge/discharge Powerwall based on solar forecast and peak/off-peak tariffs. 

Utilises the excellent [TeslaPy](https://tesla-api.timdorr.com/) by Tim Dorssers.

PwForecast is primarily designed for those with dual rate tariffs. If there is interest in expanding this to provide
more flexible control for those with more complex tariffs, please let me know. 

[![Version](https://img.shields.io/pypi/v/pwforecast)](https://pypi.org/project/pwforecast)


## Getting Started

PwForecast requires a Solcast API key and Site ID. You can sign up for a 
[free Hobbyist account](https://toolkit.solcast.com.au/register) which allows up to two sites and 50 calls per day. 

[TeslaPy](https://tesla-api.timdorr.com/) has great documentation on getting started. It even works with two factor
enabled.

Rather than wrap [TeslaPy](https://tesla-api.timdorr.com/), PwForecast requires an instance of a Tesla class passed to 
it. This allows you to configure the object based on your credentials before passing to PwForecast.  


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


## Setting Off-Peak Mode

Use this method when your off-peak rate starts. This requires a little more configuration.
 * Configure what backup reserve the Powerwall can discharge down to by setting the 'min_reserve_off_peak_rate' attribute.
 * Configure the maximum backup reserve allowed by setting the 'max_reserve' attribute. 
 * Configure the amount of energy you require during the peak-rate. 

```python
pw_forecast.min_reserve_off_peak_rate = 25  # Default 30
pw_forecast.max_reserve = 95  # Default 100
pw_forecast.required_energy_peak_rate = 20000  # Default 30000
pw_forecast.set_off_peak_mode()
```


## Advanced Configuration

PwForecast has a few advanced configuration options. Please check the class docstring for more info. 

