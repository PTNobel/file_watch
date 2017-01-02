#!/usr/bin/python3

import os
import sys
import subprocess
import time
import shared_watch
from shared_watch import Build
from typing import List, Tuple, Dict, Any, Callable, NewType

ProcessedArgs = Dict[str, Any]
Recipe = NewType("Recipe", Dict[str, Any])
MainForFileMethod = Callable[[ProcessedArgs], None]
FilePair = Tuple[MainForFileMethod, ProcessedArgs]


def usage(exit_code: int, name: object) -> None:
    usage_text = ("Usage: %s [--help|-h]" +
                  " [--sagetex|-s]" +
                  " [--biber|-b]" +
                  " [--auxdir </tmp/$USER-LaTeX>|-a </tmp/$USER-LaTeX>]" +
                  " [--engine <pdflatex>|-e <pdflatex>]" + " <file.tex>" +
                  " [--slow|-S]") % str(name)

    if exit_code == 0:
        print(usage_text)
    elif exit_code > 0:
        print(usage_text, file=sys.stderr)
    elif exit_code < 0:
        usage(exit_code, name)
    exit(exit_code)


class LaTeXBuild(Build):
    def __init__(self, recipe: Recipe) -> None:
        self.recipe = recipe
        self.addToBuild('latex')
        self.addWatchedFile(recipe['file'])

        self.pdfname = os.path.join(
            # ''[:: -1] reverses a string. So this reverses the filename, in
            # order to replace the last tex with pdf
            recipe['auxdir'],
            os.path.basename(
                recipe['file'][:: -1].replace('xet', 'fdp', 1)[:: -1]
            )
        )

        if recipe['biber']:
            self.addToBuild('biber')

        if recipe['sagetex']:
            self.addToBuild('sagetex')

        if recipe['extra_files']:
            for i in recipe['extra_files']:
                self.addWatchedFile(i)

        if recipe['biber'] or recipe['sagetex']:
            self.addToBuild('latex')

        self.addToBuild('backup')
        if recipe['make']:
            self.build_steps = [self.make]

    def latex(self):
        subprocess.call([self.recipe['engine'],
                         '-output-directory',
                         self.recipe['auxdir'],
                         "-interaction=nonstopmode", self.recipe['file']])

    def make(self):
        subprocess.call(['make'])

    def biber(self):
        subprocess.call(
            ["biber",
             "--output-directory", self.recipe['auxdir'],
                "--input-directory", self.recipe['auxdir'],
                os.path.basename(self.recipe
                                 ['file'][:: -1].replace
                                 ('xet.', '', 1)[:: -1])])

    def sagetex(self):
        firstdir = os.getcwd()
        os.chdir(self.recipe['auxdir'])
        subprocess.call(
            ['sage',
                os.path.basename(self.recipe
                                 ['file'][:: -1].replace
                                 ('xet', 'egas.xetegas', 1)[:: -1])])
        os.chdir(firstdir)

    def backup(self):
        subprocess.call(['cp', self.pdfname, os.path.expanduser('~/.latex/')])

    def addToBuild(self, nameOfCompilationStep):
        self.build_steps.append(
            {
                'latex': self.latex,
                'biber': self.biber,
                'sagetex': self.sagetex,
                'backup': self.backup,
                'make': self.make,
                'hasAnythingChanged': self.hasAnythingChanged,
            }[nameOfCompilationStep]
        )


def processargs(input_argv: List[str]) -> ProcessedArgs:
    processingArgs = shared_watch.ProcessArgs(
            input_argv,
            usage,
            LaTeXBuild,
            "LaTeX"
            )

    processingArgs.output_recipe['sagetex'] = False
    processingArgs.output_recipe['biber'] = False
    processingArgs.output_recipe['engine'] = "pdflatex"

    def _sagetex(i: int):
        processingArgs.output_recipe['sagetex'] = True
    processingArgs.long_args_to_disc['--sagetex'] = _sagetex
    processingArgs.short_args_to_disc['s'] = _sagetex

    def _biber(i: int):
        processingArgs.output_recipe['biber'] = True
    processingArgs.long_args_to_disc['--biber'] = _biber
    processingArgs.short_args_to_disc['b'] = _biber

    def _engine(i: int):
        if '=' in input_argv[i]:
            engine = input_argv[i].split('=')[1]
        else:
            engine = input_argv[i + 1]
            processingArgs.indexes_to_ignore.append(i + 1)

        processingArgs.output_recipe["engine"] = engine
    processingArgs.long_args_to_disc['--engine'] = _engine
    processingArgs.short_args_to_disc['e'] = _engine

    return processingArgs.render_processargs()


class ShouldExit():
    _num_of_returns = 0
    files_returned = []  # type: List[str]

    def __init__(self, num: int) -> None:
        self._num_of_files = num

    def returnForFile(self, name: str) -> None:
        self.files_returned.append(name)
        self._num_of_returns += 1

    def cleanTime(self) -> bool:
        if self._num_of_returns == self._num_of_files:
            return True
        else:
            return False


class SwapFilesWatch():
    _num_of_returns = 0
    swapsToCheck = []  # type: List[str]

    def __init__(self, primaryFile, extraFiles) -> None:
        self.swapsToCheck.append(os.path.join(os.path.dirname(primaryFile),
                                 '.' + os.path.basename(primaryFile) + '.swp'))
        for singleFile in extraFiles:
            self.swapsToCheck.append(os.path.join(
                os.path.dirname(singleFile),
                '.' + os.path.basename(singleFile) +
                '.swp'))

    def swapFilesExist(self):
        result = False
        for swap in self.swapsToCheck:
            if os.path.exists(swap):
                result = True
                break

        return result


def main_for_file(args: ProcessedArgs) -> None:
    os.makedirs(os.path.expandvars(args['auxdir']), exist_ok=True)
    if args['slow']:
        pdfname = os.path.join(
            # ''[:: -1] reverses a string. So this reverses the filename,
            # in order to replace the last tex with pdf and then reverses it
            # again.
            os.path.expanduser('~/.latex'),
            os.path.basename(args['file'][:: -1].replace
                             ('xet', 'fdp', 1)[:: -1]))
    else:
        pdfname = os.path.join(
            # ''[:: -1] reverses a string. So this reverses the filename,
            # in order to replace the last tex with pdf
            args['auxdir'],
            os.path.basename(args['file'][:: -1].replace
                             ('xet', 'fdp', 1)[:: -1]))
    swapWatch = SwapFilesWatch(args['file'], args['extra_files'])
    args['build'].build()
    if not args['disable_viewer']:
        subprocess.call(['rifle', pdfname])
    if os.getenv('VIM', False):
        return

    while swapWatch.swapFilesExist():
        try:
            if args['build'].hasAnythingChanged():
                args['build'].build()
            time.sleep(5)
        except KeyboardInterrupt:
            args['build'].build()

    if args['build'].hasAnythingChanged():
        args['build'].build()
        if swapWatch.swapFilesExist():
            main_for_file(args)


if __name__ == '__main__':
    main_for_file(processargs(sys.argv))
