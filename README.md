## PwForecast
A Python library to charge/discharge Powerwall based on solar forecast and peak/off peak tariffs. 

Utilises the excellent [TeslaPy](https://tesla-api.timdorr.com/) by Tim Dorssers.

Please Note: This is a work in progress. The first release tag will be applied when pwforecast is in a working state.


## Usage

Basic usage of the module:

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
    
    # Peak Mode: Sets powerwall backup reserve from the 'min_reserve_peak' setting.
    pw_forecast.min_reserve_peak = 10  # set min peak reserve, default 20.
    pw_forecast.set_peak_mode()
    
    # Off Peak Mode: Sets powerwall backup reserve based on solar forecast.
    pw_forecast.min_reserve_off_peak = 25  # set min off peak reserve, default 30.
    pw_forecast.max_reserve = 95  # set max allowed reserve, default 90.
    pw_forecast.required_energy_peak = 20000  # set energy required during peak time in Wh, default 30000.
    pw_forecast.set_off_peak_mode()
```