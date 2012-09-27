"""
The crypto module provides a layer between Dispersy and low level crypographic features.

@author: Boudewijn Schoon
@organization: Technical University Delft
@contact: dispersy@frayja.com
"""

# update version information directly from SVN
from .revision import update_revision_information
update_revision_information("$HeadURL$", "$Revision$")

if False:
    #
    # disable crypto
    #

    from random import random

    _curves = {u"very-low":42,
               u"low":60,
               u"medium":104,
               u"high":144}

    def ec_generate_key(security):
        assert isinstance(security, unicode)
        assert security in _curves

        length = _curves[security]
        private_key = "".join(chr(int(random() * 2**8)) for _ in xrange(2*length))
        public_key = private_key[:length]

        return (length, public_key, private_key)

    def ec_public_pem_to_public_bin(pem):
        return pem

    def ec_private_pem_to_private_bin(pem):
        return pem

    def ec_to_private_pem(ec, cipher=None, password=None):
        return ";".join((str(ec[0]), ec[1].encode("HEX"), ec[2].encode("HEX")))

    def ec_to_public_pem(ec):
        return ";".join((str(ec[0]), ec[1].encode("HEX"), ""))

    def ec_from_private_pem(pem, password=None):
        length, public_key, private_key = pem.split(";")
        return int(length), public_key.decode("HEX"), private_key.decode("HEX")

    def ec_from_public_pem(pem):
        length, public_key, private_key = pem.split(";")
        assert private_key == ""
        return int(length), public_key.decode("HEX"), private_key.decode("HEX")

    def ec_to_private_bin(ec):
        return ec_to_private_pem(ec)

    def ec_to_public_bin(ec):
        return ec_to_public_pem(ec)

    def ec_check_private_bin(string):
        try:
            return bool(ec_from_private_bin(string))
        except:
            return False

    def ec_check_public_bin(string):
        try:
            return bool(ec_from_public_bin(string))
        except:
            return False

    def ec_from_private_bin(string):
        return ec_from_private_pem(string)

    def ec_from_public_bin(string):
        return ec_from_public_pem(string)

    def ec_signature_length(ec):
        return ec[0]

    def ec_sign(ec, digest):
        return "".join(chr(int(random() * 2**8)) for _ in xrange(ec[0]))

    def ec_verify(ec, digest, signature):
        return True

else:
    #
    # enable crypto
    #

    from hashlib import sha1, sha224, sha256, sha512, md5
    from math import ceil
    from M2Crypto.m2 import bn_to_bin, bin_to_bn, bn_to_mpi, mpi_to_bn
    from M2Crypto import EC, BIO
    from struct import Struct

    _struct_L = Struct(">L")

    # Allow all available curves.
    _curves = dict((unicode(curve), getattr(EC, curve)) for curve in dir(EC) if curve.startswith("NID_"))

    # We want to provide a few default curves.  We will change these curves as new become available
    # and old ones to small to provide sufficient security.
    _curves.update({u"very-low":EC.NID_sect163k1,
                    u"low":EC.NID_sect233k1,
                    u"medium":EC.NID_sect409k1,
                    u"high":EC.NID_sect571r1})

    def _progress(*args):
        "Called when no feedback needs to be given."
        pass

    def ec_generate_key(security):
        """
        Generate a new Elliptic Curve object with a new public / private
        key pair.

        Security can be u'low', u'medium', or u'high' depending on how secure you need your Elliptic
        Curve to be.  Currently these values translate into:
            - very-low: NID_sect163k1  ~42 byte signatures
            - low:      NID_sect233k1  ~60 byte signatures
            - medium:   NID_sect409k1 ~104 byte signatures
            - high:     NID_sect571r1 ~144 byte signatures

        @param security: Level of security {u'very-low', u'low', u'medium', or u'high'}.
        @type security: unicode

        @note that the NID must always be 160 bits or more, otherwise it will not be able to sign a sha1
            digest.
        """
        assert isinstance(security, unicode)
        assert security in _curves
        ec = EC.gen_params(_curves[security])
        ec.gen_key()
        return ec

    def ec_public_pem_to_public_bin(pem):
        "Convert a public key in PEM format into a public key in binary format."
        return "".join(pem.split("\n")[1:-2]).decode("BASE64")

    def ec_private_pem_to_private_bin(pem):
        """
        Convert a private key in PEM format into a private key in binary format.

        @note: Enrcypted pem's are NOT supported and will silently fail.
        """
        return "".join(pem.split("\n")[1:-2]).decode("BASE64")

    def ec_to_private_pem(ec, cipher=None, password=None):
        "Get the private key in PEM format."
        def get_password(*args):
            return password or ""
        bio = BIO.MemoryBuffer()
        ec.save_key_bio(bio, cipher, get_password)
        return bio.read_all()

    def ec_to_public_pem(ec):
        "Get the public key in PEM format."
        bio = BIO.MemoryBuffer()
        ec.save_pub_key_bio(bio)
        return bio.read_all()

    def ec_from_private_pem(pem, password=None):
        "Get the EC from a private PEM."
        def get_password(*args):
            return password or ""
        return EC.load_key_bio(BIO.MemoryBuffer(pem), get_password)

    def ec_from_public_pem(pem):
        "Get the EC from a public PEM."
        return EC.load_pub_key_bio(BIO.MemoryBuffer(pem))

    def ec_to_private_bin(ec):
        "Get the private key in binary format."
        return ec_private_pem_to_private_bin(ec_to_private_pem(ec))

    def ec_to_public_bin(ec):
        "Get the public key in binary format."
        return ec_public_pem_to_public_bin(ec_to_public_pem(ec))

    def ec_check_private_bin(string):
        "Returns True if the input is a valid private key"
        try:
            ec_from_private_bin(string)
        except:
            return False
        return True

    def ec_check_public_bin(string):
        "Returns True if the input is a valid public key"
        try:
            ec_from_public_bin(string)
        except:
            return False
        return True

    def ec_from_private_bin(string):
        "Get the EC from a private key in binary format."
        return ec_from_private_pem("".join(("-----BEGIN EC PRIVATE KEY-----\n", string.encode("BASE64"), "-----END EC PRIVATE KEY-----\n")))

    def ec_from_public_bin(string):
        "Get the EC from a public key in binary format."
        return ec_from_public_pem("".join(("-----BEGIN PUBLIC KEY-----\n", string.encode("BASE64"), "-----END PUBLIC KEY-----\n")))

    def ec_signature_length(ec):
        """
        Returns the length, in bytes, of each signature made using EC.
        """
        return int(ceil(len(ec) / 8.0)) * 2

    def ec_sign(ec, digest):
        """
        Returns the signature of DIGEST made using EC.
        """
        length = int(ceil(len(ec) / 8.0))

        mpi_r, mpi_s = ec.sign_dsa(digest)
        length_r, = _struct_L.unpack_from(mpi_r)
        r = mpi_r[-min(length, length_r):]
        length_s, = _struct_L.unpack_from(mpi_s)
        s = mpi_s[-min(length, length_s):]

        return "".join(("\x00" * (length - len(r)), r, "\x00" * (length - len(s)), s))

    def ec_verify(ec, digest, signature):
        """
        Returns True when SIGNATURE matches the DIGEST made using EC.
        """
        assert len(signature) == ec_signature_length(ec), [len(signature), ec_signature_length(ec)]
        length = len(signature) / 2
        try:
            mpi_r = "".join((_struct_L.pack(length + 1), "\x00", signature[:length]))
            mpi_s = "".join((_struct_L.pack(length + 1), "\x00", signature[length:]))
            return bool(ec.verify_dsa(digest, mpi_r, mpi_s))

        except:
            return False

# def rsa_generate_key(bits=1024, exponent=5, progress=_progress):
#     """
#     Generate a new RSA object with a new public / private key pair.

#     Note: with RSA it is dangerous to use a small exponent to encrypt
#     the same message to multiple recipients, as this can lead to an
#     algebraic attack.
#     """
#     assert isinstance(bits, (int, long))
#     assert bits % 8 == 0
#     assert isinstance(exponent, int)
#     assert hasattr("__call__", progress)
#     # assert bits >= 512, "Need at least 512 bits to sign sha1 message digests"
#     return M2Crypto.RSA.gen_key(bits, exponent, progress)

# def rsa_to_private_pem(rsa, cipher="aes_128_cbc", password=None):
#     """
#     Get the private key in PEM format.
#     """
#     assert isinstance(rsa, M2Crypto.RSA.RSA)
#     assert password is None or isinstance(password, str)
#     def get_password(*args):
#         return password or "-empty-"
#     bio = M2Crypto.BIO.MemoryBuffer()
#     rsa.save_key_bio(bio, cipher, get_password)
#     return bio.read_all()

# def rsa_to_private_bin(rsa, cipher="aes_128_cbc", password=None):
#     pem = rsa_to_private_pem(rsa, cipher, password)
#     lines = pem.split("\n")
#     return "".join(lines[4:-2]).decode("BASE64")

# def rsa_to_public_pem(rsa):
#     """
#     Get the public key in binary format from RSA.

#     # note: for some reason the M2Crypto interface does not allow us
#     # to set the cipher or the password.  These two parameters are
#     # therefore ignored.
#     """
#     assert isinstance(rsa, M2Crypto.RSA.RSA)
#     bio = M2Crypto.BIO.MemoryBuffer()
#     rsa.save_pub_key_bio(bio)
#     return bio.read_all()

# def rsa_to_public_bin(rsa, cipher="aes_128_cbc", password=None):
#     pem = rsa_to_public_pem(rsa, cipher, password)
#     lines = pem.split("\n")
#     return "".join(lines[1:-2]).decode("BASE64")

# def rsa_from_private_pem(pem, password=None):
#     """
#     Create a RSA public / private key pair from a PEM binary string.
#     """
#     assert isinstance(pem, str)
#     assert password is None or isinstance(password, str)
#     def get_password(*args):
#         return password or "-empty-"
#     return M2Crypto.RSA.load_key_bio(M2Crypto.BIO.MemoryBuffer(pem), get_password)

# def rsa_from_public_pem(pem):
#     """
#     Create a RSA public part from a PEM binary string.
#     """
#     assert isinstance(pem, str)
#     return M2Crypto.RSA.load_pub_key_bio(M2Crypto.BIO.MemoryBuffer(pem))

if __debug__:
    import time

    def EC_name(curve):
        assert isinstance(curve, int)
        for name in dir(EC):
            value = getattr(EC, name)
            if isinstance(value, int) and value == curve:
                return name

    def speed():
        curves = {}
        for curve in sorted([unicode(attr) for attr in dir(EC) if attr.startswith("NID_")]):
            ec = ec_generate_key(curve)
            private_pem = ec_to_private_pem(ec)
            public_pem = ec_to_public_pem(ec)
            public_bin = ec_to_public_bin(ec)
            private_bin = ec_to_private_bin(ec)
            print
            print "generated:", time.ctime()
            print "curve:", curve, "<<<", EC_name(_curves[curve]), ">>>"
            print "len:", len(ec), "bits ~", ec_signature_length(ec), "bytes signature"
            print "pub:", len(public_bin), public_bin.encode("HEX")
            print "prv:", len(private_bin), private_bin.encode("HEX")
            print "pub-sha1", sha1(public_bin).digest().encode("HEX")
            print "prv-sha1", sha1(private_bin).digest().encode("HEX")
            print public_pem.strip()
            print private_pem.strip()

            ec2 = ec_from_public_pem(public_pem)
            assert ec_verify(ec2, "foo-bar", ec_sign(ec, "foo-bar"))
            ec2 = ec_from_private_pem(private_pem)
            assert ec_verify(ec2, "foo-bar", ec_sign(ec, "foo-bar"))
            ec2 = ec_from_public_bin(public_bin)
            assert ec_verify(ec2, "foo-bar", ec_sign(ec, "foo-bar"))
            ec2 = ec_from_private_bin(private_bin)
            assert ec_verify(ec2, "foo-bar", ec_sign(ec, "foo-bar"))

            curves[EC_name(_curves[curve])] = ec

        for key, curve in sorted(curves.iteritems()):
            t1 = time.time()

            signatures = [ec_sign(curve, str(i)) for i in xrange(100)]

            t2 = time.time()

            for i, signature in enumerate(signatures):
                ec_verify(curve, str(i), signature)

            t3 = time.time()
            print key, "signing took", round(t2-t1, 5), "verify took", round(t3-t2, 5), "totals", round(t3-t1, 5)

    def main():
        for curve in [u"very-low", u"NID_secp224r1", u"low", u"medium", u"high"]:
            ec = ec_generate_key(curve)
            private_pem = ec_to_private_pem(ec)
            public_pem = ec_to_public_pem(ec)
            public_bin = ec_to_public_bin(ec)
            private_bin = ec_to_private_bin(ec)
            print
            print "generated:", time.ctime()
            print "curve:", curve, "<<<", EC_name(_curves[curve]), ">>>"
            print "len:", len(ec), "bits ~", ec_signature_length(ec), "bytes signature"
            print "pub:", len(public_bin), public_bin.encode("HEX")
            print "prv:", len(private_bin), private_bin.encode("HEX")
            print "pub-sha1", sha1(public_bin).digest().encode("HEX")
            print "prv-sha1", sha1(private_bin).digest().encode("HEX")
            print public_pem.strip()
            print private_pem.strip()
