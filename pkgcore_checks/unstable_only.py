# Copyright: 2006 Brian Harring <ferringb@gmail.com>
# License: GPL2

from pkgcore.restrictions import packages, values
from pkgcore_checks.base import Template, package_feed, Result
from pkgcore_checks import addons


class UnstableOnly(Result):

    """package/keywords that are strictly unstable"""

    __slots__ = ("category", "package", "version", "arch")
    
    threshold = package_feed

    def __init__(self, pkgs, arch):
        Result.__init__(self)
        self._store_cp(pkgs[0])
        self.arch = arch
        self.version = tuple(x.fullver for x in pkgs)

    @property
    def short_desc(self):
        return "for arch %s, all versions are unstable: [ %s ]" % (
            self.arch, ', '.join(self.version))
    
    def to_str(self):
        return "%s/%s: arch %s, all unstable: [ %s ]" % \
            (self.category, self.package, self.arch, ", ".join(self.version))


class UnstableOnlyReport(Template):
    """scan for pkgs that have just unstable keywords"""

    feed_type = package_feed
    required_addons = (addons.ArchesAddon,)
    known_results = (UnstableOnly,)

    def __init__(self, options, arches):
        Template.__init__(self, options)
        arches = set(x.strip().lstrip("~") for x in options.arches)
        # stable, then unstable, then file
        self.arch_restricts = {}
        for x in arches:
            self.arch_restricts[x] = [
                packages.PackageRestriction("keywords",
                    values.ContainmentMatch(x)),
                packages.PackageRestriction("keywords",
                    values.ContainmentMatch("~%s" % x))
                ]

    def feed(self, pkgset, reporter):
        # stable, then unstable, then file
        for k, v in self.arch_restricts.iteritems():
            stable = unstable = None
            for x in pkgset:
                if v[0].match(x):
                    stable = x
                    break
            if stable is not None:
                continue
            unstable = [x for x in pkgset if v[1].match(x)]
            if unstable:
                reporter.add_report(UnstableOnly(unstable, k))

    def finish(self, reporter):
        self.arch_restricts.clear()
