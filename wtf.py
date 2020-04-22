import sys
# import urlparse
import pprint


def main(args):
    # Make sure we have only one arg, the URL
    if len(args) != 1:
        return 1

    # Parse the URL:
    protocol, fullPath = args[0].split(":", 1)
    path, fullArgs = fullPath.split("?", 1)
    action = path.strip("/")
    args = fullArgs.split("&")
    # params = urlparse.parse_qs(fullArgs)

    # This is where you can do something productive based on the params and the
    # action value in the URL. For now we'll just print out the contents of the
    # parsed URL.
    fh = open('output.txt', 'w')
    fh.write(pprint.pformat((action)))
    fh.close()


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))