from argparse import ArgumentParser, REMAINDER
from datetime import timedelta
from netsnmp import snmpget, snmpwalk, Varbind
from os import environ, path
from re import search
from subprocess import CalledProcessError, check_output, STDOUT
from sys import argv, exit
import time

usage = 'Usage: python %s <printer_address>...' % argv[0]

'''Printer Monitor.

Check any number of Ricoh printers for errors. Filter option to ignore selected errors.

Options:
  -a=TRUE --all=TRUE   Turn off filtering (default FALSE)
'''

mibs_dir = path.abspath(path.join(path.dirname( __file__ ), '..', 'mibs'))
mibs_to_load = mibs_dir + '/Printer-MIB.my:' + mibs_dir + '/DISMAN-EVENT-MIB.txt' #colon-separated (!) list
environ['MIBS'] = mibs_to_load

ignore_list = 'low:|lite:|no paper|tomt for papir|low power mode|energy saver mode|energisparemodus|modus for lavt str|warming up|varmer opp|nearly full|nesten full|not detected: tray|finner ikke: magasin|not detected: input|mismatch: paper size and type|passer ikke: papirformat og type|current job suspended|adjusting|offline|frakoblet'

def ping(host, times=1):
    '''Silently pings the host once. Returns true if host answers; false if it doesn't.'''
    try:
        check_output(['ping', '-c', str(times), host], stderr=STDOUT, universal_newlines=True)
    except CalledProcessError:
        return False
    return True

def walk_mib(device_address, mib):
    '''Returns the value of all children of the given Management Information Base (MIB) for a network device'''
    return snmpwalk(Varbind(mib), DestHost = device_address, Community = 'public', Version = 1)

def get_mib(device_address, mib):
    '''Returns the value of the given Management Information Base (MIB) for a network device'''
    return snmpget(Varbind(mib), DestHost = device_address, Community = 'public', Version = 1)

def get_printer_errors(printer_address, ignore_list, all=False, pings=1):
    '''Returns all errors from a printer'''
    if ping(printer_address, pings): #TODO: impliment some actual error handling
        err_descriptions = list(walk_mib(printer_address, 'prtAlertDescription.1'))
        err_ticks = list(walk_mib(printer_address, 'prtAlertTime.1'))
        if err_descriptions:
            parsed_errors = ''
            system_uptime_ticks = int(get_mib(printer_address, 'sysUpTimeInstance')[0])
            location = get_mib(printer_address, 'sysLocation.0')[0].split(',')[2]
            for index, description in enumerate(err_descriptions):
                err_desc = description.split('{')[0] 
                if all or not search(ignore_list, err_desc.lower()):
                    err_time = str(timedelta(seconds=(system_uptime_ticks - int(err_ticks[index]))/100))
                    parsed_errors += '%s (%s): %s in %s\n' % (printer_address.split('.')[0].upper(), location, err_desc, err_time)
            return parsed_errors
        else:
            return ''
    else:
        return '%s: host \'%s\' unknown or offline\n' % (printer_address.split('.')[0].upper(), printer_address)

if __name__ == '__main__':
    parser = ArgumentParser(usage=usage)
    parser.add_argument('-a', '--all',
        default=False,
        help='Display all errors')
    parser.add_argument('-p', '--pings',
        default=1,
        help='More pings takes more time, but gives less false positives')
    parser.add_argument('args', nargs=REMAINDER)
    args = parser.parse_args()

    if len(args.args) > 0:
        start_time = time.time()
        errors = ''
        for arg in args.args:
            errors += get_printer_errors(arg, ignore_list, args.all, args.pings)
        end_time = time.time()
        if len(errors) > 0:
            print errors.replace('\xe6', 'ae').replace('\xf8', 'oe').replace('\xe5', 'aa')
            print 'DONE: %i printers checked in %.1f seconds' % (len(args.args), end_time - start_time)
    else:
        print usage; exit(1)
