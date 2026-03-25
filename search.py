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


def arbeitsagentur_search(params):
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
