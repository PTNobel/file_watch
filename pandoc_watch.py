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


def usage(exit_code: int, name: object):
    usage_text = ("Usage: %s [--help|-h]" +
                  " [--auxdir </tmp/$USER-Pandoc>|-a </tmp/$USER-Pandoc>]" +
                  " <file.tex>" +
                  " [--slow|-S]") % str(name)

    if exit_code == 0:
        print(usage_text)
    elif exit_code > 0:
        print(usage_text, file=sys.stderr)
    elif exit_code < 0:
        usage(exit_code, name)
    exit(exit_code)


class PandocBuild(Build):
    def __init__(self, recipe: Recipe) -> None:
        self.build_map = {
            'pandoc': self.pandoc
        }
        self.recipe = recipe  # type: Recipe
        self.addToBuild('pandoc')
        if recipe["docx"]:
            _output_file_extension = 'docx'[::-1]
        elif recipe["outputType"]:
            _output_file_extension = recipe["outputType"][::-1]
        else:
            _output_file_extension = 'pdf'[::-1]

        self.outputName = os.path.join(
            # ''[:: -1] reverses a string. So this reverses the filename, in
            # order to replace the last md with pdf
            recipe['auxdir'],
            os.path.basename(
                recipe['file'][:: -1].replace(
                    'dm', _output_file_extension, 1
                )[:: -1]
            )
        )

        if recipe["docx"]:
            self.pdfname = ""
        else:
            self.pdfname = self.outputName

        self.addWatchedFile(recipe['file'])

    def pandoc(self):
        print('Started building', self.recipe['file'] + '.')
        subprocess.call(
            ['pandoc'] + self.recipe['pandoc_options'] + [
                '-o',
                self.outputName,
                self.recipe['file']
            ]
            )
        print('Finished building', self.recipe['file'] + '.')


def processargs(input_argv: List[str]) -> ProcessedArgs:
    processingArgs = shared_watch.ProcessArgs(
            input_argv,
            usage,
            PandocBuild,
            "Pandoc"
            )

    processingArgs.output_recipe['docx'] = False
    processingArgs.output_recipe['outputType'] = False
    processingArgs.output_recipe['pandoc_options'] = []

    def _output_type(i: int):
        if '=' in input_argv[i]:
            out_type = input_argv[i].split('=')[1]
        else:
            out_type = input_argv[i + 1]
            processingArgs.indexes_to_ignore.append(i + 1)

        processingArgs.output_recipe["outputType"] = out_type
        processingArgs.output["outputType"] = out_type

    def _docx(i: int):
        processingArgs.output_recipe["docx"] = True
        processingArgs.output["docx"] = True
        processingArgs._disable_viewer(i)
    processingArgs.long_args_to_disc['--docx'] = _docx
    processingArgs.short_args_to_disc['d'] = _docx

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

    def __init__(self, primaryFile: str, extraFiles: List[str]) -> None:
        self.swapsToCheck.append(os.path.join(os.path.dirname(primaryFile),
                                 '.' + os.path.basename(primaryFile) + '.swp'))
        for singleFile in extraFiles:
            self.swapsToCheck.append(os.path.join(
                os.path.dirname(singleFile),
                '.' + os.path.basename(singleFile) +
                '.swp'))

    def swapFilesExist(self) -> bool:
        result = bool()
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
        pdfname = args['build'].pdfname
    print(pdfname)
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
