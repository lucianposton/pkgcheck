from collections import defaultdict
from itertools import chain

from pkgcore.restrictions import packages, values
from snakeoil.strings import pluralism as _pl

from .. import addons, base


class PotentialStable(base.VersionedResult, base.Warning):
    """Stable arches with potential stable package candidates."""

    __slots__ = ("slot", "keywords", "stable")

    def __init__(self, pkg, keywords):
        super().__init__(pkg)
        self.slot = pkg.slot
        self.keywords = tuple(sorted(keywords))
        self.stable = tuple(sorted(str(arch) for arch in pkg.keywords
                            if not arch[0] in ("~", "-")))

    @property
    def short_desc(self):
        return "slot(%s), stabled arch%s: [ %s ], potential%s: [ %s ]" % (
            self.slot, _pl(self.stable, plural='es'), ', '.join(self.stable),
            _pl(self.keywords), ', '.join(self.keywords))


class LaggingStable(base.VersionedResult, base.Warning):
    """Stable arches for stabilized package that are lagging from a stabling standpoint."""

    __slots__ = ("slot", "keywords", "stable")

    def __init__(self, pkg, keywords):
        super().__init__(pkg)
        self.slot = pkg.slot
        self.keywords = tuple(sorted(keywords))
        self.stable = tuple(sorted(str(arch) for arch in pkg.keywords
                            if not arch[0] in ("~", "-")))

    @property
    def short_desc(self):
        return "slot(%s), stabled arch%s: [ %s ], lagging: [ %s ]" % (
            self.slot, _pl(self.stable, plural='es'),
            ', '.join(self.stable), ', '.join(self.keywords))


class ImlateCheck(base.Check):
    """Scan for ebuilds that are lagging in stabilization."""

    feed_type = base.package_feed
    required_addons = (addons.StableArchesAddon,)
    known_results = (PotentialStable, LaggingStable)

    @staticmethod
    def mangle_argparser(parser):
        parser.plugin.add_argument(
            "--source-arches", action='csv', metavar='ARCH',
            help="comma separated list of arches to compare against for lagging stabilization",
            docs="""
                Comma separated list of arches to compare against for
                lagging stabilization.

                The default arches are all stable arches (unless --arches is specified).
            """)

    def __init__(self, options, stable_arches=None):
        super().__init__(options)
        self.all_arches = frozenset(options.arches)
        self.stable_arches = frozenset(arch.strip().lstrip("~") for arch in options.stable_arches)
        self.target_arches = frozenset(
            "~%s" % arch.strip().lstrip("~") for arch in self.stable_arches)

        source_arches = options.source_arches
        if source_arches is None:
            source_arches = options.stable_arches
        self.source_arches = frozenset(
            arch.lstrip("~") for arch in source_arches)
        self.source_filter = packages.PackageRestriction(
            "keywords", values.ContainmentMatch2(self.source_arches))

    def feed(self, pkgset):
        pkg_slotted = defaultdict(list)
        for pkg in pkgset:
            pkg_slotted[pkg.slot].append(pkg)

        fmatch = self.source_filter.match
        for slot, pkgs in sorted(pkg_slotted.items()):
            slot_keywords = set(chain.from_iterable(pkg.keywords for pkg in pkgs))
            stable_slot_keywords = self.all_arches.intersection(slot_keywords)
            potential_slot_stables = {'~' + x for x in stable_slot_keywords}
            newer_slot_stables = set()
            for pkg in reversed(pkgs):
                # only consider pkgs with keywords that contain the targeted arches
                if not fmatch(pkg):
                    newer_slot_stables.update(self.all_arches.intersection(pkg.keywords))
                    continue

                lagging_stables = potential_slot_stables.intersection(pkg.keywords)
                lagging_stables -= {'~' + x for x in newer_slot_stables}
                if lagging_stables:
                    yield LaggingStable(pkg, lagging_stables)

                unstable_keywords = {x for x in pkg.keywords if x[0] == '~'}
                potential_stables = self.target_arches.intersection(unstable_keywords)
                potential_stables -= lagging_stables
                if potential_stables:
                    yield PotentialStable(pkg, potential_stables)

                break
