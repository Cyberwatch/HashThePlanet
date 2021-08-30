# HashThePlanet

Computes hashs for all JS, TXT and CSS files for each tag in a repository.
Generates a database file in `dist` directory which stores all the results.

## Usage

First, create a virtual environnement.

```bash
python3 -m venv venv
source venv/bin/activate
```

Then, use the `make` command to install the requirements and the project.

```bash
make install
```

Finally, call the **`hashtheplanet`** executable.

```bash
hashtheplanet -h
```

