#!/usr/bin/python3

import latex_watch
import pandoc_watch
import shared_watch
import sys
import os
from threading import Thread
from typing import List, Tuple, Dict, Any, Callable

ProcessedArgs = Dict[str, Any]
MainForFileMethod = Callable[[ProcessedArgs], None]
FilePair = Tuple[MainForFileMethod, ProcessedArgs]


def processargs(
        argv: List[str],
        ) -> List[FilePair]:
    output = list()  # type: List[FilePair]
    dashArguments = False
    markdownFiles = False
    latexFiles = False
    # Skip the name of the program
    for arg in argv[1:]:
        if arg[0] == '-':
            dashArguments = True
        elif '.md' in arg[-3:]:
            markdownFiles = True
        elif '.tex' in arg[-4:]:
            latexFiles = True

    if not dashArguments and len(argv) > 1:
        for arg in argv[1:]:
            if '.md' in arg[-3:]:
                output.append(
                        (
                            pandoc_watch.main_for_file,
                            pandoc_watch.processargs([argv[0], arg])
                        )
                )

            elif '.tex' in arg[-4:]:
                output.append(
                        (
                            latex_watch.main_for_file,
                            latex_watch.processargs([argv[0], arg])
                        )
                )

    elif markdownFiles and latexFiles:
        exit(1)
    elif markdownFiles:
        output.append(
                (
                    pandoc_watch.main_for_file,
                    pandoc_watch.processargs(argv)
                )
        )

    elif latexFiles:
        output.append(
                (
                    latex_watch.main_for_file,
                    latex_watch.processargs(argv)
                )
        )
    else:
        # No file name given: discover the .tex/.md files vim has open in this
        # directory and watch them. Vim may write the swap file next to the
        # file (".foo.tex.swp"), or, as configured on this machine, into a
        # central swap directory (shared_watch.VIM_SWAP_DIR); check both.
        cwd = os.getcwd()
        open_files = []  # type: List[str]

        for file_name in os.listdir():
            if len(file_name) > 5 and file_name[0] == '.' and \
                    file_name[-4:] == '.swp':
                open_files.append(os.path.join(cwd, file_name[1:-4]))

        for open_file in shared_watch.vim_swapped_files():
            if os.path.dirname(open_file) == cwd:
                open_files.append(open_file)

        seen = set()  # type: set
        for open_file in open_files:
            if open_file in seen:
                continue
            seen.add(open_file)

            if open_file[-4:] == '.tex':
                output.append(
                        (
                            latex_watch.main_for_file,
                            latex_watch.processargs(argv + [open_file])
                        )
                )
            elif open_file[-3:] == '.md':
                output.append(
                        (
                            pandoc_watch.main_for_file,
                            pandoc_watch.processargs(argv + [open_file])
                        )
                )
    return output


def launchWatches(mainsAndArgs: List[FilePair]) -> None:
    for mainAndArgPair in mainsAndArgs:
        Thread(
            target=mainAndArgPair[0],
            args=tuple([mainAndArgPair[1]]),
            ).start()


if __name__ == '__main__':
    launchWatches(processargs(sys.argv))
