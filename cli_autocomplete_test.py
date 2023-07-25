#!/usr/bin/env python
# PYTHON_ARGCOMPLETE_OK

import argparse
import argcomplete

class MyCLITool:
    def __init__(self):
        self.parser = argparse.ArgumentParser(description="A CLI tool with auto-completion")
        self.parser.add_argument("command", choices=["list", "create", "delete"], help="Command to execute")
        self.parser.add_argument("-f", "--file", metavar="FILE", help="Path to the input file")
        argcomplete.autocomplete(self.parser)
        # self.args = self.parser.parse_args()


        args = self.parser.parse_args()
        
        if args.command == "list":
            print("Listing resources...")
        elif args.command == "create":
            print("Creating resource...")
            if args.file:
                print(f"Using file: {args.file}")
        elif args.command == "delete":
            print("Deleting resource...")

def main():
    cli_tool = MyCLITool()
    # cli_tool.run()

if __name__ == "__main__":
    main()