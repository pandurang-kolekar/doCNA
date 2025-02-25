import argparse
import configparser
import os
import shutil
import subprocess
import sys

import pandas as pd
from doCNA.Run import Solution

from doCNA import WGS
from doCNA import Models

_description = "Scan chromosomes in search for non-HE segments. Assigns copy numbers if can."

__version__ = '0.9.1'


def main():
    parser = argparse.ArgumentParser (prog="docna", description = _description)
    subparsers = parser.add_subparsers(title="actions", dest="action")
    subparsers.required = True

    ### Analyze subparser ###
    parser_analyze = subparsers.add_parser("analyze", description="runs the analysis")
    parser_analyze.add_argument ('-s', '--sample_name', required = False, 
                                 type = str, default = '',
                                 help = 'Input sample name. Default: from file name.')
    parser_analyze.add_argument ('-n', '--no_processes', required = False, default = 1, type = int,
                                 help = 'Number of processes. Default: 1')
    parser_analyze.add_argument ('-i', '--input_file', required = True,
                                 type = str, default = '',
                                 help = "Name of the input file with alleles' counts")
    parser_analyze.add_argument ('-c', '--config', required = False, default = 'config.ini',
                                 help = 'INI file with parameters')
    parser_analyze.add_argument ('-l', '--level', default = 'INFO', 
                                 choices = ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL', 'NOTSET'],
                                 help = 'Level of verbosity for std.err logger.')
    parser_analyze.add_argument ('-r', '--report_solutions', help = 'Generate report with all solutions.',
                                 action = 'store_true')
    parser_analyze.add_argument ('-m0', '--coverage_diploid', required = False, type = float,
                                 help = 'Coverage of diploid.', default = 0)    
    parser_analyze.add_argument ('-v', '--version', help = 'Print version', action = 'version',
                                 version = 'doCNA v. {version}'.format(version = __version__))
    parser_analyze.add_argument ('-m', '--models', choices=Models.model_presets_extra.keys(),
                                 nargs='+', help = 'Specify which of extra models should be included.',
                                 default = [])
    parser_analyze.set_defaults (func=analyze)

    ### Viewer subparser ###
    parser_viewer = subparsers.add_parser ("viewer", description="launches the viewer")
    parser_viewer.add_argument ('--remote', action="store_true",
                                help="use a if running from a remote machine, for example a compute cluster")
    parser_viewer.add_argument ('-p', '--port', type=str, help="specific port to use")
    parser_viewer.set_defaults (func=viewer)

    ### Get Config subparser ###
    get_config = subparsers.add_parser ("getconfig", description="copies default docna config to current dir")
    get_config.add_argument ("-d", "--directory", default=os.getcwd(),
                             help="copies config to this dir. Default is current working directory.")
    get_config.set_defaults (func=get_docna_config)

    args = parser.parse_args()
    args.func(args)

def analyze(args):
    """ runs the analysis """
    ini = configparser.ConfigParser ()
    ini.read (args.config)
    sample = WGS.WGS (args.input_file,  sample_name = args.sample_name, parameters = ini,
                      no_processes = args.no_processes,
                      verbosity = args.level)

    sample.analyze (m0 = args.coverage_diploid)

    model_presets = {}
    model_presets.update (Models.model_presets_2)
    model_presets.update (Models.model_presets_4)

    for model in args.models:
        model_presets[model] = Models.model_presets_extra[model]    
    

    with open (args.sample_name + '.bed', 'w') as bed:
        bed.writelines (sample.report(report_type = 'bed'))

    with open (args.sample_name + '.par', 'w') as params:
        params.writelines (sample.report (report_type = 'params'))

    if args.report_solutions:
        with open (args.sample_name + '.solutions', 'w') as full:
            full.writelines (sample.report(report_type = 'solution'))

    keys = sample.genome.chromosomes.keys()
    data = pd.concat ([sample.genome.chromosomes[k].data for k in keys])

    data.to_csv (args.sample_name + '.dat.gz', index = None, sep = '\t', 
                 compression = 'gzip')

    print ('All done')

def viewer(args):
    """ launches the viewer - we get a port not in use"""
    import socket
    s = socket.socket()
    hostname = socket.gethostname()
    host_to_use = socket.gethostbyname(hostname)
    s.bind(("", 0))
    open_port = str(s.getsockname()[1])
    s.close()
    if args.port:
        open_port = args.port
    if not args.remote:
        host_to_use = "localhost"
    cmd = ["shiny", "run", "--port", open_port, "--host", host_to_use, "doCNA.viewer.app"]
    print("**********")
    print(f"Access dashboard in browser via: http://{host_to_use}:{open_port}")
    print("**********")

    proc = subprocess.run(cmd, stdout=sys.stdout, stderr=sys.stderr)    

def get_docna_config(args):
    """ local helper to copy config to current working directory """
    configdir = os.path.dirname (os.path.realpath(__file__))
    shutil.copyfile (f'{configdir}/doCNA.ini', f'{args.directory}/doCNA.ini')
    

if __name__ == '__main__':
    sys.exit(main())
