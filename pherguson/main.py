#!/usr/bin/env python

from .core.application import GopherApplication


def main():
    """Main entry point for Pherguson"""
    app = GopherApplication()
    app.run()


if __name__ == "__main__":
    main() 