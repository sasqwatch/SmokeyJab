#!/usr/bin/env python
"""A provisioning tool for the SmokeyJab framework"""
import argparse
import base64
import json
import logging
import math
import os
import random
import string
import zlib
import sys

BASE_DIR = os.path.abspath(os.path.dirname(__name__))

all_params = {}


def time_breakdown(_s):
    _s, s = divmod(int(_s), 60)
    _s, m = divmod(_s, 60)
    _s, h = divmod(_s, 24)
    return (_s, h, m, s)


def hrtime(x):
    return '{}d {}h {}m {}s'.format(*time_breakdown(x))


def terminal_size():
    import fcntl, termios, struct
    h, w, hp, wp = struct.unpack('HHHH',
                                 fcntl.ioctl(0, termios.TIOCGWINSZ,
                                             struct.pack('HHHH', 0, 0, 0, 0)))
    return w, h


def compile_modules(tags, getvars_only=False):
    global all_params
    tags = set(tags)
    module_dir = os.path.join(BASE_DIR, 'framework', 'modules')
    module_list = []
    module_times = []  # [(delay, duration, start_time, name), ...]
    for fname in os.listdir(module_dir):
        if not fname.endswith('.py'):
            logging.debug('Skipping "{}"'.format(fname))
            continue
        with open(os.path.join(module_dir, fname)) as f:
            logging.debug('Attempting to load plugins from "{}"'.format(fname))
            module_code = f.read()

            # Test the modules
            _globals = {}
            _locals = {}
            module_args = all_params.get(fname, {})

            try:
                exec (module_code, _globals, _locals)
            except Exception as e:
                logging.error('Problem testing the modules: {}'.format(e))
                sys.exit(1)
            for module_name, module in _locals.items():
                if module_name in ('ModuleBase', 'Utils'):
                    continue

                logging.info('Checking class "{}"...'.format(module_name))
                try:
                    instance = module('')
                except Exception as e:
                    logging.info('Error testing this item, skipping [{}]'.format(e))
                    continue

                # Make sure module version number is implemented
                try:
                    assert isinstance(instance.VERSION, (str, unicode))
                    logging.debug('`-> Module version: v{}'.format(instance.VERSION))
                except (AssertionError, AttributeError):
                    logging.error('`-> Module version not specified')
                    continue

                # Make sure relative_delay is implemented
                try:
                    logging.debug('`-> Relative delay: {}%'.format(instance.relative_delay))
                except NotImplementedError:
                    logging.error('`-> relative_delay not specified for this module')
                    continue

                # Make sure absolute_duration is implemented
                try:
                    logging.debug('`-> Module duration: {} seconds'.format(instance.absolute_duration))
                except NotImplementedError:
                    logging.error('`-> absolute_duration not specified for this module')
                    continue

                # Check if tags were specified and if so, ensure the module has all required tags
                if tags:
                    instance_tags = set(instance.tags)
                    if tags - instance_tags:
                        logging.warning('`-> Module does not have all required tags, skipping')
                        module_code = ''
                        break
                    else:
                        logging.debug('`-> Tags found: "{}"'.format('", "'.join(instance_tags & tags)))

                # Save time constraints
                module_times.append((instance.relative_delay, instance.absolute_duration, 0, instance.module_name))

                # Check for variables
                t = string.Template(module_code)
                while True:
                    try:
                        t.substitute(module_args)
                    except KeyError as e:
                        (key,) = e.args
                        if not getvars_only:
                            value = raw_input('Input a value for {}::{}> '.format(module_name, key))
                        else:
                            value = ''
                        module_args[key] = value
                    else:
                        break
                module_code = t.substitute(module_args)
                all_params[fname] = module_args

            module_list.append(module_code)
    all_module_code = '\n\n'.join(module_list)

    # Return if all we wanted was to populate a list of variables
    if getvars_only:
        return None, None, None, None

    # Compute engagement duration. This is determined by finding the smallest window such that all modules can execute
    # with their given delays and durations within the window.
    def get_rec_duration(window):
        for delay, duration, _, _ in module_times:
            window = max(delay * window / 100.0 + duration, window)
        return window

    minimum_engagement_duration = int(max([x for _, x, _, _ in module_times]))
    rec_duration = get_rec_duration(minimum_engagement_duration)

    while True:
        logging.warning('Minimum engagement time: {} seconds ({})'.format(minimum_engagement_duration,
                                                                          hrtime(minimum_engagement_duration)))
        logging.warning('Recommended engagement time: {} seconds ({})'.format(rec_duration, hrtime(rec_duration)))
        input_engagement_duration = raw_input('How long (seconds) do you want this engagement to run? ')
        try:
            input_engagement_duration = int(input_engagement_duration)
            assert input_engagement_duration >= minimum_engagement_duration
        except:
            continue
        else:
            break

    # Module start is computed as the delay factor multiplied by the user-supplied engagement length
    # If this is anticipated to overrun the total expected engagement time, then the module will start
    # as late as possible in the engagement.
    for k, (delay, duration, _, module_name) in enumerate(module_times):
        module_start = input_engagement_duration * delay / 100.0
        if module_start + duration > input_engagement_duration:
            module_start = input_engagement_duration - duration
        module_times[k] = (delay, duration, module_start, module_name)

    framework_end_time = 0

    for delay, duration, start, name in module_times:
        end_time = start + duration
        framework_end_time = max(end_time, framework_end_time)
    logging.debug('The framework is expected to finish after {} seconds ({})'.format(framework_end_time,
                                                                                     hrtime(
                                                                                         framework_end_time)))

    logging.debug('Total size of prepared modules: {} bytes'.format(len(all_module_code)))
    return module_times, framework_end_time, input_engagement_duration, all_module_code


def generate_filename(min_length):
    with open('/usr/share/dict/words') as f:
        wordlist = filter(lambda x: x.isalpha(), f.read().split())
    outfile = random.choice(wordlist)
    while len(outfile) < min_length:
        outfile = random.choice(wordlist) + '_' + outfile
    outfile += '.py'
    return outfile.lower()


def provision_framework(modules, exercise_duration, module_delays, args):
    modules_string = base64.b64encode(zlib.compress(modules))
    logging.info('Compressed modules to {} bytes'.format(len(modules_string)))
    with open(os.path.join(BASE_DIR, 'framework', 'main.py')) as f:
        framework = f.read()
    t = string.Template(framework)
    return t.substitute(ALL_CODE_LIST=modules_string, SPLUNK_HOST=args.splunk_host, SPLUNK_TOKEN=args.splunk_token,
                        SCRIPT_NAME=args.script_name, REDTEAM_TAG=args.banner, PROJECT_NAME=args.project,
                        EXERCISE_DURATION=exercise_duration, MODULE_DELAYS=json.dumps(module_delays))


def main():
    global all_params

    parser = argparse.ArgumentParser()
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging')
    parser.add_argument('-c', '--config', default='config.json', help='Load a configuration file')
    parser.add_argument('-g', '--gen-config', action='store_true', help='Generate a module config template and exit')
    parser.add_argument('-b', '--banner', default='.: If found, please contact the red team :.',
                        help='Tag to insert into artifacts for identification purposes')
    parser.add_argument('-n', '--script-name', default='/usr/bin/salt-minion',
                        help='New name for the script in the process list')
    parser.add_argument('-u', '--splunk-host', default=None, help='The host (server[:port]) of the splunk HEC')
    parser.add_argument('-t', '--splunk-token', default=None, help='Splunk HEC token')
    parser.add_argument('-p', '--project', default=None, help='The name of the project this is running under')
    parser.add_argument('--module-tags', default=[], nargs='*', help='Include only modules with the specified tags')
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    elif args.verbose:
        logging.getLogger().setLevel(logging.INFO)

    if not args.gen_config and (args.splunk_host is None or args.splunk_token is None or args.project is None):
        parser.error('If not generating a config file, you must provide Splunk HEC host and token and a project name!')
        return

    # Attempt to load configuration file
    try:
        with open(args.config) as f:
            all_params = json.load(f)
    except Exception as e:
        logging.warning('Skipping loading configuration file ({})'.format(e))
        logging.debug(str(e))

    outfile = generate_filename(len(args.script_name))

    times, total_duration, exercise_duration, modules = compile_modules(args.module_tags, getvars_only=args.gen_config)

    if args.gen_config:
        with open(args.config, 'w') as f:
            json.dump(all_params, f, indent=4)
        logging.warning('Wrote module configuration template to {}'.format(args.config))
        return

    else:
        module_delays = {name: delay for (_, _, delay, name) in times}

    with open(outfile, 'w') as f:
        f.write(provision_framework(modules, exercise_duration, module_delays, args))

    print('Provision successful! Written to "{}"'.format(outfile))

    print('')
    print('The test is requested to last {}s ({})'.format(exercise_duration, hrtime(exercise_duration)))
    print('The last module is expected to finish after {}s ({})'.format(total_duration, hrtime(total_duration)))
    print('\nThe timeline is as follows:\n')
    columns, _ = terminal_size()
    WIDTH = columns - 76 - 5
    print('{:<30s} {:<5s} {:<16s} {:<7s} {:<16s} {}'.format('Module', 'Delay', '', 'Duration', '', 'Relative Timeline'))
    for delay, duration, start, name in sorted(times, key=lambda x: x[0]):
        s = int(1.0 * start / exercise_duration * WIDTH)
        d = int(math.ceil(1.0 * duration / exercise_duration * WIDTH))
        fms = '{:<30s} {:>5d} {:>16s} {:>7d} {:>16s} {}'
        print(fms.format(name, delay, hrtime(int(start)), duration, hrtime(duration), ' ' * s + '*' * d))


if __name__ == '__main__':
    logging.basicConfig()
    main()
