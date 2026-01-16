#!/usr/bin/env python

"""
Pherguson - A Gopher Protocol Client
Refactored version with separated concerns
"""

from pherguson.core.application import GopherApplication


def main():
    """Main entry point for Pherguson"""
    app = GopherApplication()
    app.run()


if __name__ == "__main__":
    main()
