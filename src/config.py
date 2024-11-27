from configparser import ConfigParser

def config(filename="database.ini", section="postgresql"):

    parser = ConfigParser()

    parser.read(filename)

    db = {}

    if parser.has_section(section):
        params = parser.items(section)
        for param in params:
            db[param[0]] = param[1]
    else:
        raise Exception(
            "A Section{0} cannot be found in the {1} file provided.".format(section, filename)
        )
    return db
