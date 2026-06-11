"""
Module to configure and run search on arbeitsagentur.de
"""

from urllib.parse import quote

import requests
from bs4 import BeautifulSoup


HEADERS = {
        "User-Agent": "Jobsuche/2.9.2 (de.arbeitsagentur.jobboerse; "
                      "build:1077; iOS 15.1.0) Alamofire/5.4.4",
        "Host": "rest.arbeitsagentur.de",
        "X-API-Key": "jobboerse-jobsuche",
        "Connection": "keep-alive",
    }
API_URL = ("https://rest.arbeitsagentur.de/jobboerse/jobsuche-service/pc"
               "/v4/app/jobs")
PARAMS = {
    "was": "Freitext suche Jobtitel",
    "wo": "Freitext suche Beschäftigungsort",
    "veroeffentlichtseit": "Anzahl der Tage, seit der Job veröffentlicht "
                           "wurde. Kann zwischen 0 und 100 Tagen liegen.",
    "angebotsart": "1=ARBEIT; 2=SELBSTAENDIGKEIT, 4=AUSBILDUNG/Duales Studium,"
                   " 34=Praktikum/Trainee",
    "befristung": "Semikolon-separierte mehrere Werte möglich (z.B. befristung"
                  "=1;2) 1 = befristet; 2 = unbefristet",
    "arbeitszeit": "Semikolon-separierte mehrere Werte möglich (z.B. "
                   "arbeitszeit=vz;tz) vz=VOLLZEIT, tz=TEILZEIT, snw="
                   "SCHICHT_NACHTARBEIT_WOCHENENDE, ho=HEIM_TELEARBEIT, "
                   "mj=MINIJOB",
    "umkreis": "Umkreis in Kilometern von Wo-Parameter. (z.B. 25 oder 200)"
}
PARAMS_DEFAULTS = {
    "was": "python",
    "wo": "Berlin",
    "veroeffentlichtseit": "7",
    "angebotsart": "1",
    "befristung": "1;2",
    "arbeitszeit": "vz;tz",
    "umkreis": "25"
}
JOB_URL_PREFIX = 'https://www.arbeitsagentur.de/jobsuche/jobdetail/'
DETAILS_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) "
                  "Chrome/120.0.0.0 Safari/537.36"
}
DESCRIPTION_ELEMENT_ID = "detail-beschreibung-text-container"


def parse_description_internal(job_url):
    """Fetch an internal posting's page and extract its description text.

    Downloads the job detail page hosted on arbeitsagentur.de and returns the
    text of the description element.

    Args:
        job_url: URL of the internal job detail page.

    Returns:
        Plain-text job description, or None if the request fails or the
        description element is not found.
    """
    response = requests.get(job_url, headers=DETAILS_HEADERS, verify=True)
    if response.status_code != 200:
        print(f"Status code: {response.status_code}. Failed to fetch job "
              f"details from {job_url}")
        return None
    soup = BeautifulSoup(response.text, "html.parser")
    container = soup.find(id=DESCRIPTION_ELEMENT_ID)
    if container is None:
        return None
    return container.get_text("\n", strip=True)


def parse_description_external(job_url):
    """Build a placeholder description for an externally hosted posting.

    External postings have no description on arbeitsagentur.de, so the text
    points the reader to the external page instead.

    Args:
        job_url: URL of the external job posting.

    Returns:
        A short string referring to the external posting.
    """
    return f"See details at {job_url}"


def normalize(job):
    """Convert a raw job dictionary to the standard record format.

    For internal postings the URL is built from JOB_URL_PREFIX and the
    posting's reference number. For external postings (those carrying an
    "externeUrl") the URL is the external one.

    Args:
        job: A job dictionary as returned by search().

    Returns:
        Dictionary with the standard keys "id", "title", "company",
        "location", "published" and "url". The job ID is the posting's
        reference number (refnr).
    """
    url = job.get("externeUrl")
    if not url:
        url = JOB_URL_PREFIX + quote(job["refnr"], safe="")
    return {
        "id": job["refnr"],
        "title": job.get("titel") or job.get("beruf", ""),
        "company": job.get("arbeitgeber", ""),
        "location": job.get("arbeitsort", {}).get("ort", ""),
        "published": job.get("aktuelleVeroeffentlichungsdatum", ""),
        "url": url,
    }


def description(record):
    """Return the description text for a normalized job record.

    Descriptions of internal postings are extracted from their detail page
    on arbeitsagentur.de. External postings have no description there, so
    the text points the reader to the external page instead.

    Args:
        record: A job record as returned by normalize().

    Returns:
        Plain-text job description, or None if it cannot be fetched.
    """
    if record["url"].startswith(JOB_URL_PREFIX):
        return parse_description_internal(record["url"])
    return parse_description_external(record["url"])


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
    jobs = []
    page = 1
    while True:
        query = {**params, "page": str(page)}
        response = requests.get(API_URL, headers=HEADERS, params=query,
                                verify=True)
        if response.status_code != 200:
            print(f"Status code: {response.status_code}. Failed to fetch data "
                  "from arbeitsagentur.de")
            return None
        jobs_to_add = response.json().get("stellenangebote")
        if jobs_to_add is not None:
            jobs.extend(jobs_to_add)
            page += 1
        else:
            break
    return jobs


def update_config(config=None):
    """
    Update parameters to configure search on https://www.arbeitsagentur.de.

    Args:
        config: Optional dictionary with existing parameters to modify.
                If None, default parameters will be used.

    Returns:
        Dictionary with configuration parameters.
    """
    new_config = config.copy() if config else PARAMS_DEFAULTS.copy()
    for key, value in PARAMS.items():
        print(value)
        print(f"Will be set to: [{new_config[key]}]")
        new_value = input("Enter a new value or press Enter to keep current: ")
        if new_value:
            new_config[key] = new_value
    return new_config


def get_config(config=None):
    """
    Ask user for search parameters until a working configuration is received
    or the user exits.

    Args:
        config: Optional dictionary with existing parameters to modify.
                If None, default parameters will be used.

    Returns:
        Dictionary with configuration parameters, or None if the user exits.
    """
    new_config = config.copy() if config else PARAMS_DEFAULTS.copy()
    while True:
        new_config = update_config(config=new_config)
        if search(new_config) is not None:
            return new_config
        elif input("Invalid configuration. Do you want to update it? "
                   "[yes/no]") == "no":
            break
    return None