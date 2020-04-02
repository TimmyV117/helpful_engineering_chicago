from requests import get, HTTPError
from datetime import date
import pandas as pd
import civis
import os
import logging

# Tim Velasquez
# Environment requirements in ppe_requests_ETL_requirements.txt
# Script to get PPE requests from various hospitals through GetUsPPE.org
# Also found this after experimenting with scraping:
#  https://github.com/findftm/findftm

_URL = 'https://findthemasks.com/data.json'

# Set to False if you want to export locally
_TO_PLATFORM = False

# Database information for exporting to platform
_DATABASE = ''
_SCHEMA = ''
_TABLE_PREFIX = ''

# Date suffix
today = date.today()
_DATE_SUFFIX = today.strftime('%Y%m%d')

# Filepath information for exporting locally
home = os.path.expanduser("~")
_LOCAL_EXPORT_PATH = os.path.join(home, 'Downloads')
_FILENAME = f'{_TABLE_PREFIX}_{_DATE_SUFFIX}.csv'  # ex: ftm_ppe_requests_20200328

_LOG = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO,
                    format="'%(asctime)s - %(levelname)s: %(message)s'")

def _get_data(url):
    """Calls URL to get data initially as string and
       turns it into a Pandas dataframe
    Parameters
    ----------
    url: str URL string leading to PPE request data

    Returns
    -------
    raw_dict: dict Dictionary form of response"""

    assert isinstance(url, str)

    _LOG.info('Retrieving data...')
    try:

        blob = get(url)

    except HTTPError as e:

        status_code = e.response.status_code
        _LOG.info(f'HTTP error: {status_code}')
        _LOG.error('Data retreival FAILED')
        raise

    raw_dict = eval(blob.text)
    _LOG.info('Data retrieval SUCCESSFUL!')
    return raw_dict


def _clean_raw_response(raw_dict):
    """Cleans up the raw response dataframe
    Parameters
    ----------
    raw_dict: dict Raw response dictionary from _get_data()

    Returns
    -------
    clean_df: pd.DataFrame cleaned usable responses"""

    assert isinstance(raw_dict, dict)
    assert 'values' in list(raw_dict.keys())  # information we care about is in 'values' key
    assert len(raw_dict['values']) > 0

    _LOG.info('Cleaning data...')
    values_df = pd.DataFrame(raw_dict['values'])
    values_df = values_df.iloc[1:].reset_index(drop=True)  # table comes in with two header rows so only grab one
    values_df.rename(columns=values_df.iloc[0], inplace=True)  # renames columns with first row values
    values_df.drop([0], inplace=True)  # once you rename, drop the first row

    values_df.reset_index(drop=True, inplace=True)  # final index reset

    clean_df = values_df.copy(deep=True)

    _LOG.info('Cleaning SUCCESSFUL!')

    return clean_df


def _to_redshift(clean_df):
    """Export clean_df from _clean_raw_response() to Redshift
    Parameters
    ----------
    clean_df: pd.DataFrame
    schema: str
    table: str

    Returns
    -------
    status: str Successful or not in export to redshift"""

    _LOG.info('Pushing to Redshift...')

    table = f"{_SCHEMA}.{_TABLE_PREFIX}_{_DATE_SUFFIX}"

    # TODO: error handling
    fut = civis.io.dataframe_to_civis(clean_df,
                                      _DATABASE,
                                      table,
                                      # delimiter='|',
                                      existing_table_rows='drop')
    status = fut.result()

    _LOG.info(status)
    _LOG.info(f'Table name: {table}')


def _to_csv(clean_df):
    _LOG.info('Exporting locally...')

    filepath = f'{_LOCAL_EXPORT_PATH}/{_FILENAME}'
    clean_df.to_csv(filepath,
                    index=False)

    _LOG.info('Local export SUCCESSFUL!')

    _LOG.info(f'Export path: {filepath}')


def main():
    """Orchestrates the data refresh"""
    raw_dict = _get_data(_URL)
    clean_df = _clean_raw_response(raw_dict)
    if _TO_PLATFORM:
        _to_redshift(clean_df)
        _LOG.info('PPE request refresh completed and pushed to platform')
    else:
        _LOG.info('PPE request refresh exported locally')
        _to_csv(clean_df)


if __name__ == "__main__":
    main()
