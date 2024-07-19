import resources.lib.addon as addon

if __name__ == '__main__':
    # Call the router function and pass the plugin call parameters to it.
    # We use string slicing to trim the leading '?' from the plugin call paramstring
    addon.router(sys.argv[2][1:])