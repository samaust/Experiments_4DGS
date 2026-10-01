"""Canonical S1 calibration attempt identities; recognition grants no authority."""
import re

PREFIX = 'S1-calibration-recovery-'


def is_recovery_job(job):
    """Recognize historical and fresh identities without an aggregate attempt cap."""
    return type(job) is str and re.fullmatch(
        r'S1-calibration-recovery-(?:00[1-9]|0[1-9][0-9]|[1-9][0-9]{2,})', job) is not None


def is_standing_retry_job(job):
    """Identify the fresh standing-policy series beginning at010."""
    return is_recovery_job(job) and job[len(PREFIX):] not in {f'{index:03d}' for index in range(1, 10)}


def job_from_attempt(index):
    if type(index) is not int or index < 1:
        raise ValueError('positive integer S1 attempt required')
    return PREFIX + f'{index:03d}'


def prior_job(job):
    if not is_recovery_job(job):
        raise ValueError('canonical S1 recovery identity required')
    index = int(job[len(PREFIX):])
    return job_from_attempt(index - 1) if index > 1 else None
