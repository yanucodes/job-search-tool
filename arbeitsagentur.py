"""
Module to configure and run search on arbeitsagentur.de
"""

import requests


BFA_HEADERS = {
        'User-Agent': 'Jobsuche/2.9.2 (de.arbeitsagentur.jobboerse; '
                      'build:1077; iOS 15.1.0) Alamofire/5.4.4',
        'Host': 'rest.arbeitsagentur.de',
        'X-API-Key': 'jobboerse-jobsuche',
        'Connection': 'keep-alive',
    }
BFA_API_URL = ('https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc'
               '/v4/app/jobs')
BFA_PARAMS = {
    'was': 'Freitext suche Jobtitel',
    'wo': 'Freitext suche Beschäftigungsort',
    'veroeffentlichtseit': 'Anzahl der Tage, seit der Job veröffentlicht '
                           'wurde. Kann zwischen 0 und 100 Tagen liegen.',
    'angebotsart': '1=ARBEIT; 2=SELBSTAENDIGKEIT, 4=AUSBILDUNG/Duales Studium,'
                   ' 34=Praktikum/Trainee',
    'befristung': 'Semikolon-separierte mehrere Werte möglich (z.B. befristung'
                  '=1;2) 1 = befristet; 2 = unbefristet',
    'arbeitszeit': 'Semikolon-separierte mehrere Werte möglich (z.B. '
                   'arbeitszeit=vz;tz) vz=VOLLZEIT, tz=TEILZEIT, snw='
                   'SCHICHT_NACHTARBEIT_WOCHENENDE, ho=HEIM_TELEARBEIT, '
                   'mj=MINIJOB',
    'umkreis': 'Umkreis in Kilometern von Wo-Parameter. (z.B. 25 oder 200)'
}
BFA_PARAMS_DEFAULTS = {
    'was': 'python',
    'wo': 'Berlin',
    'veroeffentlichtseit': '7',
    'angebotsart': '1',
    'befristung': '1;2',
    'arbeitszeit': 'vz;tz',
    'umkreis': '25'
}


def search(params):
    """
    Search for jobs on https://www.arbeitsagentur.de.
    Parameters can be found here: https://jobsuche.api.bund.dev/
    API endpoint and headers based on:
    https://github.com/bundesAPI/jobsuche-api

    Args:
        params: Parameters for job search query.

    Returns:
        List of dictionaries with information about jobs, or None if GET
        request fails.
    """
    response = requests.get(BFA_API_URL, headers=BFA_HEADERS,
                            params=params, verify=True)
    if response.status_code == 200:
        return response.json().get('stellenangebote', [])
    print(f"Status code: {response.status_code}. Failed to fetch data "
          "from arbeitsagentur.de")
    return None


def update_arbeitsagentur_config(config=None):
    """
    Update parameters to configure search on https://www.arbeitsagentur.de.

    Args:
        config: dictionary with parameters to modify, if None a default
                configuration will be used.

    Returns:
        Dictionary with configuration parameters.
    """
    if config is None:
        new_config = BFA_PARAMS_DEFAULTS.copy()
    else:
        new_config = config.copy()
    for key, value in BFA_PARAMS.items():
        print(value)
        print(f'Will be set to: [{BFA_PARAMS_DEFAULTS[key]}]')
        new_value = input('Enter a new value or press Enter to keep current: ')
        if user_input:
            new_config[key] = new_value
