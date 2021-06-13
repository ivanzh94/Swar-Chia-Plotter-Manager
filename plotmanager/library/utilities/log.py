import datetime
import dateparser
import logging
import os
import psutil
import re
import socket

from plotmanager.library.utilities.instrumentation import increment_plots_completed
from plotmanager.library.utilities.notifications import send_notifications
from plotmanager.library.utilities.print import pretty_print_time


def get_log_file_name(log_directory, job, datetime):
    return os.path.join(log_directory, f'{job.name}_{str(datetime).replace(" ", "_").replace(":", "_").replace(".", "_")}.log')


def get_start_time(log_file_name):
    # added
    match = re.search(
        ".*_(?P<date>\d{4}(?:-\d{2}){2})_(?P<time>\d{2}(?:_\d{2}){2})_\d{6}.log",
        log_file_name
    )
    if not match:
        return False
    date = match.group("date")
    time = match.group("time").replace("_", ":")
    return " ".join((date, time))


def _analyze_log_end_date(contents, log_file_name):
    # modified
    match = re.search(
        r'total plot creation time was (?P<seconds>[\d\.]+) sec',
        contents,
        flags=re.I
    )
    if not match:
        return False
    total_seconds = match.group("seconds")
    total_seconds = pretty_print_time(int(float(total_seconds)))
    start_time = get_start_time(log_file_name)
    if not start_time:
        return False
    parsed_date = dateparser.parse(start_time)
    return dict(
        total_seconds=total_seconds,
        date=parsed_date,
    )


def _get_date_summary(analysis):
    summary = analysis.get('summary', {})
    for file_path in analysis['files'].keys():
        if analysis['files'][file_path]['checked']:
            continue
        analysis['files'][file_path]['checked'] = True
        end_date = analysis['files'][file_path]['data']['date'].date()
        if end_date not in summary:
            summary[end_date] = 0
        summary[end_date] += 1
    analysis['summary'] = summary
    return analysis


def _get_regex(pattern, string, flags=re.I):
    return re.search(pattern, string, flags=flags).groups()


def get_completed_log_files(log_directory, skip=None):
    # modified
    if not skip:
        skip = []
    files = {}
    for file in os.listdir(log_directory):
        if file[-4:] not in ['.log', '.txt']:
            continue
        file_path = os.path.join(log_directory, file)
        if file_path in skip:
            continue
        f = open(file_path, 'r')
        try:
            contents = f.read()
        except UnicodeDecodeError:
            continue
        f.close()
        if 'Total plot creation time was' not in contents:
            continue
        files[file_path] = contents
    return files


def analyze_log_dates(log_directory, analysis):
    # modified
    files = get_completed_log_files(log_directory, skip=list(analysis['files'].keys()))
    for file_path, contents in files.items():
        data = _analyze_log_end_date(contents, file_path)
        if data is None:
            continue
        analysis['files'][file_path] = {'data': data, 'checked': False}
    analysis = _get_date_summary(analysis)
    return analysis


def analyze_log_times(log_directory):
    # modified
    total_times = {1: 0, 2: 0, 3: 0, 4: 0}
    line_numbers = {1: [], 2: [], 3: [], 4: []}
    count = 0
    files = get_completed_log_files(log_directory)
    for file_path, contents in files.items():
        count += 1
        phase_times, phase_dates = get_phase_info(contents, pretty_print=False, log_file_path=file_path)
        for phase, seconds in phase_times.items():
            total_times[phase] += seconds
        splits = contents.split('Phase')
        phase = 0
        new_lines = 1
        for split in splits:
            phase += 1
            if phase >= 5:
                break
            new_lines += split.count('\n')
            line_numbers[phase].append(new_lines)

    for phase in range(1, 5):
        print(f'  phase{phase}_line_end: {int(round(sum(line_numbers[phase]) / len(line_numbers[phase]), 0))}')

    for phase in range(1, 5):
        print(f'  phase{phase}_weight: {round(total_times[phase] / sum(total_times.values()) * 100, 2)}')

def get_phase_info(contents, view_settings=None, pretty_print=True, log_file_path=None):
    # modified
    if not view_settings:
        view_settings = {}
    phase_times = {}
    phase_dates = {}

    phase_seconds = {}
    start_datetime = None
    if log_file_path is not None:
        start_datetime = dateparser.parse(get_start_time(log_file_path))
    for phase in range(1, 5):
        if log_file_path is None or start_datetime is None:
            continue
        match = re.search(rf'Phase {phase} took (?P<seconds>[\d\.]+) sec', contents, flags=re.I)
        if match:
            seconds = match.group('seconds')
            seconds = float(seconds)
            phase_seconds[phase] = seconds
            phase_times[phase] = pretty_print_time(
                int(seconds),
                view_settings['include_seconds_for_phase']
            ) if pretty_print else seconds
            phase_dates[phase] = start_datetime + datetime.timedelta(seconds=sum(phase_seconds.values()))

    return phase_times, phase_dates


def get_progress(line_count, progress_settings):
    # modified
    phase1_line_end = progress_settings['phase1_line_end']
    phase2_line_end = progress_settings['phase2_line_end']
    phase3_line_end = progress_settings['phase3_line_end']
    phase4_line_end = progress_settings['phase4_line_end']
    phase1_weight = progress_settings['phase1_weight']
    phase2_weight = progress_settings['phase2_weight']
    phase3_weight = progress_settings['phase3_weight']
    phase4_weight = progress_settings['phase4_weight']
    progress = 0

    if line_count > phase1_line_end:
        progress += phase1_weight
    else:
        progress += phase1_weight * ((line_count - 10 if line_count > 10 else 0) / phase1_line_end) + \
                    (int((10 / phase1_line_end) * phase1_weight) / 8 * (line_count - 10)) * 0.85 \
            if line_count > 10 else 0
        return progress
    if line_count > phase2_line_end:
        progress += phase2_weight
    else:
        progress += phase2_weight * ((line_count - phase1_line_end) / (phase2_line_end - phase1_line_end))
        return progress
    if line_count > phase3_line_end:
        progress += phase3_weight
    else:
        progress += phase3_weight * ((line_count - phase2_line_end) / (phase3_line_end - phase2_line_end))
        return progress
    if line_count > phase4_line_end:
        progress += phase4_weight
    else:
        progress += phase4_weight * ((line_count - phase3_line_end) / (phase4_line_end - phase3_line_end))
    return progress


def check_log_progress(jobs, running_work, progress_settings, notification_settings, view_settings,
                       instrumentation_settings):
    for pid, work in list(running_work.items()):
        logging.info(f'Checking log progress for PID: {pid}')
        if not work.log_file:
            continue
        f = open(work.log_file, 'r')
        data = f.read()
        f.close()

        line_count = (data.count('\n') + 1)

        progress = get_progress(line_count=line_count, progress_settings=progress_settings)

        phase_times, phase_dates = get_phase_info(data, view_settings, log_file_path=work.log_file)
        current_phase = 1
        if phase_times:
            current_phase = max(phase_times.keys()) + 1
        work.phase_times = phase_times
        work.phase_dates = phase_dates
        work.current_phase = current_phase
        work.progress = f'{progress:.2f}%'

        if psutil.pid_exists(pid) and 'Started copy to ' not in data.lower():
            logging.info(f'PID still alive: {pid}')
            continue

        logging.info(f'PID no longer alive: {pid}')
        for job in jobs:
            if not job or not work or not work.job:
                continue
            if job.name != work.job.name:
                continue
            logging.info(f'Removing PID {pid} from job: {job.name}')
            if pid in job.running_work:
                job.running_work.remove(pid)
            job.total_running -= 1
            job.total_completed += 1
            increment_plots_completed(increment=1, job_name=job.name, instrumentation_settings=instrumentation_settings)

            send_notifications(
                title='Plot Completed',
                body=f'You completed a plot on {socket.gethostname()}!',
                settings=notification_settings,
            )
            break
        del running_work[pid]
