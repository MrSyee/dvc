from __future__ import unicode_literals

import os
import re

import dvc.logger as logger
from dvc.command.base import fix_subparsers
from dvc.config import Config
from dvc.remote import _get, RemoteLOCAL
from dvc.command.config import CmdConfig


class CmdRemoteAdd(CmdConfig):
    @staticmethod
    def resolve_path(path, config_file):
        """Resolve path relative to config file location.

        Args:
            path: Path to be resolved.
            config_file: Path to config file, which `path` is specified
                relative to.

        Returns:
            Path relative to the `config_file` location. If `path` is an
            absolute path then it will be returned without change.

        """
        if os.path.isabs(path):
            return path
        return os.path.relpath(path, os.path.dirname(config_file))

    def run(self):
        remote = _get({Config.SECTION_REMOTE_URL: self.args.url})
        if remote == RemoteLOCAL:
            self.args.url = self.resolve_path(
                self.args.url, self.configobj.filename
            )

        section = Config.SECTION_REMOTE_FMT.format(self.args.name)
        ret = self._set(section, Config.SECTION_REMOTE_URL, self.args.url)
        if ret != 0:
            return ret

        if self.args.default:
            msg = "Setting '{}' as a default remote.".format(self.args.name)
            logger.info(msg)
            ret = self._set(
                Config.SECTION_CORE, Config.SECTION_CORE_REMOTE, self.args.name
            )

        return ret


class CmdRemoteRemove(CmdConfig):
    def _remove_default(self, config):
        core = config.get(Config.SECTION_CORE, None)
        if core is None:
            return 0

        default = core.get(Config.SECTION_CORE_REMOTE, None)
        if default is None:
            return 0

        if default == self.args.name:
            return self._unset(
                Config.SECTION_CORE,
                opt=Config.SECTION_CORE_REMOTE,
                configobj=config,
            )

    def run(self):
        section = Config.SECTION_REMOTE_FMT.format(self.args.name)
        ret = self._unset(section)
        if ret != 0:
            return ret

        for configobj in [
            self.config._local_config,
            self.config._repo_config,
            self.config._global_config,
            self.config._system_config,
        ]:
            self._remove_default(configobj)
            self.config.save(configobj)
            if configobj == self.configobj:
                break

        return 0


class CmdRemoteModify(CmdConfig):
    def run(self):
        section = Config.SECTION_REMOTE_FMT.format(self.args.name)
        self.args.name = "{}.{}".format(section, self.args.option)
        return super(CmdRemoteModify, self).run()


class CmdRemoteDefault(CmdConfig):
    def run(self):
        self.args.value = self.args.name
        self.args.name = "core.remote"
        return super(CmdRemoteDefault, self).run()


class CmdRemoteList(CmdConfig):
    def run(self):
        for section in self.configobj.keys():
            r = re.match(Config.SECTION_REMOTE_REGEX, section)
            if r:
                name = r.group("name")
                url = self.configobj[section].get(
                    Config.SECTION_REMOTE_URL, ""
                )
                logger.info("{}\t{}".format(name, url))
        return 0


def add_parser(subparsers, parent_parser):
    from dvc.command.config import parent_config_parser

    REMOTE_HELP = "Manage set of tracked repositories."
    remote_parser = subparsers.add_parser(
        "remote",
        parents=[parent_parser],
        description=REMOTE_HELP,
        help=REMOTE_HELP,
    )

    remote_subparsers = remote_parser.add_subparsers(
        dest="cmd",
        help="Use dvc remote CMD --help for " "command-specific help.",
    )

    fix_subparsers(remote_subparsers)

    REMOTE_ADD_HELP = "Add remote."
    remote_add_parser = remote_subparsers.add_parser(
        "add",
        parents=[parent_config_parser, parent_parser],
        description=REMOTE_ADD_HELP,
        help=REMOTE_ADD_HELP,
    )
    remote_add_parser.add_argument("name", help="Name.")
    remote_add_parser.add_argument(
        "url",
        help="URL. See full list of supported urls at "
        "https://dvc.org/doc/commands-reference/remote",
    )
    remote_add_parser.add_argument(
        "-d",
        "--default",
        action="store_true",
        default=False,
        help="Set as default remote.",
    )
    remote_add_parser.set_defaults(func=CmdRemoteAdd)

    REMOTE_DEFAULT_HELP = "Set/unset default remote."
    remote_default_parser = remote_subparsers.add_parser(
        "default",
        parents=[parent_config_parser, parent_parser],
        description=REMOTE_DEFAULT_HELP,
        help=REMOTE_DEFAULT_HELP,
    )
    remote_default_parser.add_argument(
        "name", nargs="?", help="Name of the remote."
    )
    remote_default_parser.add_argument(
        "-u",
        "--unset",
        action="store_true",
        default=False,
        help="Unset default remote.",
    )
    remote_default_parser.set_defaults(func=CmdRemoteDefault)

    REMOTE_REMOVE_HELP = "Remove remote."
    remote_remove_parser = remote_subparsers.add_parser(
        "remove",
        parents=[parent_config_parser, parent_parser],
        description=REMOTE_REMOVE_HELP,
        help=REMOTE_REMOVE_HELP,
    )
    remote_remove_parser.add_argument("name", help="Name")
    remote_remove_parser.set_defaults(func=CmdRemoteRemove)

    REMOTE_MODIFY_HELP = "Modify remote."
    remote_modify_parser = remote_subparsers.add_parser(
        "modify",
        parents=[parent_config_parser, parent_parser],
        description=REMOTE_MODIFY_HELP,
        help=REMOTE_MODIFY_HELP,
    )
    remote_modify_parser.add_argument("name", help="Name.")
    remote_modify_parser.add_argument("option", help="Option.")
    remote_modify_parser.add_argument("value", nargs="?", help="Value.")
    remote_modify_parser.add_argument(
        "-u",
        "--unset",
        default=False,
        action="store_true",
        help="Unset option.",
    )
    remote_modify_parser.set_defaults(func=CmdRemoteModify)

    REMOTE_LIST_HELP = "List remotes."
    remote_list_parser = remote_subparsers.add_parser(
        "list",
        parents=[parent_config_parser, parent_parser],
        description=REMOTE_LIST_HELP,
        help=REMOTE_LIST_HELP,
    )
    remote_list_parser.set_defaults(func=CmdRemoteList)
