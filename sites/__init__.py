"""Nazurin site plugins & plugin manager."""
from importlib import import_module
from re import search
from glob import glob
from os import path
from utils import logger
from config import ADMIN_ID
from telegram.ext import Filters

class SiteManager(object):
    """Site plugin manager."""

    def __init__(self):
        """Initialize."""
        self.sites = dict()
        self.commands = list()
        self.sources = list()

    def load(self):
        """Dynamically load all site plugins."""
        module_paths = glob('sites/*/')
        for module_path in module_paths:
            module_name = path.basename(path.normpath(module_path))
            if module_name.startswith('__'):
                continue
            module = import_module('sites.' + module_name)
            self.sites[module_name.lower()] = getattr(module, module_name)()
            if hasattr(module, 'commands'):
                self.commands += getattr(module, 'commands')
            if hasattr(module, 'patterns') and hasattr(module, 'handle'):
                PRIORITY = getattr(module, 'PRIORITY')
                patterns = getattr(module, 'patterns')
                handle = getattr(module, 'handle')
                self.sources.append((PRIORITY, patterns, handle, module_name))
            self.sources.sort(key=lambda s: s[0], reverse=True)
        logger.info("Sites loaded")

    def api(self, site):
        return self.sites[site]

    def register_commands(self, dispatcher):
        adminFilter = Filters.user(user_id=ADMIN_ID)
        for command in self.commands:
            command.filters = command.filters & adminFilter
            dispatcher.add_handler(command)

    def match(self, urls):
        sources = self.sources
        urls = str.join(',', urls)
        result = None
        matched_priority = 0

        for interface in sources:
            priority, patterns, handle, site_name = interface
            if priority < matched_priority:
                break
            for pattern in patterns:
                match = search(pattern, urls)
                if match:
                    result = {
                        'match': match,
                        'site': site_name,
                        'handler': handle
                    }
                    matched_priority = priority
                    break

        if not result:
            return False
        return result

    def handle_update(self, result):
        handle = result['handler']
        return handle(result['match'])
