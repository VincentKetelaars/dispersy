from random import shuffle
from socket import gethostbyname, error
from threading import Lock
from time import time

from .callback import Callback
from .candidate import BootstrapCandidate
from .logger import get_logger
logger = get_logger(__name__)

# Note that some the following DNS entries point to the same IP addresses.  For example, currently
# both DISPERSY1.TRIBLER.ORG and DISPERSY1.ST.TUDELFT.NL point to 130.161.211.245.  Once these two
# DNS entries are resolved only a single BootstrapCandidate is made.  This requires a potential
# attacker to disrupt the DNS servers for both domains at the same time.
_DEFAULT_ADDRESSES = (
    # DNS entries on tribler.org
    (u"dispersy1.tribler.org", 6421),
    (u"dispersy2.tribler.org", 6422),
    (u"dispersy3.tribler.org", 6423),
    (u"dispersy4.tribler.org", 6424),
    (u"dispersy5.tribler.org", 6425),
    (u"dispersy6.tribler.org", 6426),
    (u"dispersy7.tribler.org", 6427),
    (u"dispersy8.tribler.org", 6428),

    # DNS entries on st.tudelft.nl
    (u"dispersy1.st.tudelft.nl", 6421),
    (u"dispersy2.st.tudelft.nl", 6422),
    (u"dispersy3.st.tudelft.nl", 6423),
    (u"dispersy4.st.tudelft.nl", 6424),
    (u"dispersy5.st.tudelft.nl", 6425),
    (u"dispersy6.st.tudelft.nl", 6426),
    (u"dispersy7.st.tudelft.nl", 6427),
    (u"dispersy8.st.tudelft.nl", 6428))

# 04/12/13 Boudewijn: We are phasing out the dispersy{1-9}b entries.  Note that older clients will
# still assume these entries exist!
# (u"dispersy1b.tribler.org", 6421),
# (u"dispersy2b.tribler.org", 6422),
# (u"dispersy3b.tribler.org", 6423),
# (u"dispersy4b.tribler.org", 6424),
# (u"dispersy5b.tribler.org", 6425),
# (u"dispersy6b.tribler.org", 6426),
# (u"dispersy7b.tribler.org", 6427),
# (u"dispersy8b.tribler.org", 6428),

# _DEFAULT_ADDRESSES = _DEFAULT_ADDRESSES + tuple((u"rotten.dns.entry%d.org" % i, 1234) for i in xrange(8))


class Bootstrap(object):

    @staticmethod
    def load_addresses_from_file(filename):
        """
        Reads FILENAME and returns the hosts therein, otherwise returns an empty list.
        """
        addresses = []
        try:
            for line in open(filename, "r"):
                line = line.strip()
                if not line.startswith("#"):
                    host, port = line.split()
                    addresses.append((host.decode("UTF-8"), int(port)))
        except:
            pass

        return addresses

    @staticmethod
    def get_default_addresses():
        """
        Returns the predefined default addresses.
        """
        return _DEFAULT_ADDRESSES

    def __init__(self, callback, addresses):
        assert isinstance(callback, Callback), type(callback)
        assert isinstance(addresses, (tuple, list)), type(addresses)
        assert all(isinstance(address, tuple) for address in addresses), [type(address) for address in addresses]
        assert all(len(address) == 2 for  address in addresses), [len(address) for address in addresses]
        assert all(isinstance(host, unicode) for host, _ in addresses), [type(host) for host, _ in addresses]
        assert all(isinstance(port, int) for _, port in addresses), [type(port) for _, port in addresses]
        self._callback = callback
        self._lock = Lock()
        self._candidates = dict((address, None) for address in addresses)
        self._thread_counter = 0

    @property
    def are_resolved(self):
        """
        Returns True when all addresses are resolved.

        Note: this method is thread safe.
        """
        with self._lock:
            return all(self._candidates.itervalues())

    @property
    def candidates(self):
        """
        Returns all *resolved* BootstrapCandidate instances.

        Note: this method is thread safe.
        """
        with self._lock:
            return [candidate for candidate in self._candidates.itervalues() if candidate]

    @property
    def progress(self):
        """
        Returns a (resolved_count, total_count) tuple.

        Note: this method is thread safe.
        """
        with self._lock:
            return (len([candidate for candidate in self._candidates.itervalues() if candidate]),
                    len(self._candidates))

    def reset(self):
        """
        Removes all previously resolved addresses.

        Note: this method is thread safe.
        """
        with self._lock:
            self._candidates = dict((address, None) for address in self._candidates.iterkeys())

    def resolve(self, func, timeout=60.0, blocking=False):
        """
        Resolve all unresolved trackers on a separate thread.

        FUNC is called on the self._callback thread when either:
        1. all trackers are resolved (with True as the first parameter), or
        2. after TIMEOUT seconds (with False as the first parameter).

        Note: this method is thread safe.
        """
        assert isinstance(timeout, float), type(timeout)
        assert timeout > 0.0, timeout
        assert isinstance(blocking, bool), type(blocking)

        if self.are_resolved:
            self._callback.register(func, (True,))

        else:
            self._thread_counter += 1

            # start a new thread (using Callback to ensure the thread is named properly)
            thread = Callback("Resolve-%d" % self._thread_counter)
            thread.start()
            if blocking:
                thread.call(self._gethostbyname_in_parallel, (func, timeout), timeout=timeout)
                thread.stop()
            else:
                thread.register(self._gethostbyname_in_parallel, (func, timeout))
                thread.register(thread.stop)

    def _gethostbyname_in_parallel(self, func, timeout):
        begin = time()
        success = True

        with self._lock:
            addresses = [address for address, candidate in self._candidates.iteritems() if not candidate]
            shuffle(addresses)

        for host, port in addresses:
            if time() - begin > timeout:
                # timeout
                success = False
                break

            try:
                candidate = BootstrapCandidate((gethostbyname(host), port), False)
                logger.debug("resolved %s into %s", host, candidate)

                with self._lock:
                    self._candidates[(host, port)] = candidate

            except error:
                logger.exception("unable to obtain BootstrapCandidate(%s, %d)", host, port)
                success = False

        # indicate results are ready
        self._callback.register(func, (success,))
