# HypoMeals
[![pipeline status](https://gitlab.oit.duke.edu/hypomeals/hypomeals/badges/master/pipeline.svg)](https://gitlab.oit.duke.edu/hypomeals/hypomeals/commits/master)

HypoMeals is a sophisticated food manufacturing management software. It features SKU and ingredients managment, product lines, and much more.

## Developer Guide

### Prerequisites

* [Docker Commmunity Edition](https://hub.docker.com/search/?type=edition&offering=community)
* [Docker Compose 1.8](https://docs.docker.com/compose/install/) or above. Depending on the host OS, this may or may not be bundled with Docker.
* [Python 3.7](https://www.python.org/) or above
* [Git](https://git-scm.com/)
* (Optional) [PyCharm Professional](https://www.jetbrains.com/pycharm/)

### Getting Started

To get started, first clone the repository onto your computer

```bash
git clone git@gitlab.oit.duke.edu:hypomeals/hypomeals.git
cd hypomeals
```

#### HTTPS Certificates

The project uses the HTTPS protocol. For security reasons, the certificates and private keys are not included in the repository. **They must be obtained separately before running the project.** The certificates are distributed in a file named `certs.zip`: it contains a directory named `certs` which must be placed under the `nginx/` directory. In order words, the directory tree of the `nginx/` directory should look like:

```
nginx
├── certs
│   ├── vcm-4081.vm.duke.edu.key
│   └── vcm-4081.vm.duke.edu.pem
└── config
    └── web-app.conf
```

**Note:** the certificates are self-issued, which means most modern browsers will warn you that the certificate is not trusted. This is fine, and the warning should be dismissed.

However, the certificates are issued with an extension called `Subject Alternative Name`s, and will certify three hosts: `vcm-4081.vm.duke.edu` (the production server), `127.0.0.1` and `localhost`. What that means is that, although your browser may warn about untrusted issuer, it **should not** warn about an invalid common name, if the project is being deployed locally.

Once ther certificates are obtained, there are then two ways to run the project: using Docker directly, or setting up a virtual environment.

#### Virtual Environment (Recommended)

A virtual environment may be much better suited for development, because some IDEs can automatically detect and run the Django project, if the environment is set up correctly. To set up a new virtual environment on a Unix host, use these commands under the root directory of the project:

```bash
# This will set up a fresh environment under a directory named venv/
python -m venv venv/
# This will "activate" the new virtual environment
source venv/bin/activate
```

For tutorials and guides on setting up virtual environments on other OSes, check the [official documentation](https://docs.python.org/3/library/venv.html#module-venv).

Once the virtual environment is activated, install all project requirements:

```
pip install -r hypomeals/requirements.txt
```

Then, to start the Django development server, use the command:

```bash
cd hypomeals/
python manage.py runserver 8000
```

Finally, to see the website, go to `http://127.0.0.1:8000` on your browser. 

#### Docker

The project is designed to be deployed by a Docker engine. A `docker-compose.yml` is provided so that the containers may be spun up easily all at once. In the root directory of the project, simply type

```bash
sudo docker-compose up
```

**Note:** `sudo` may not be required on Windows or macOS computers.

Once the containers are all set up, visit `https://127.0.0.1` on your host computer.

### Code Style

Several languages are used throughout the project. To facilitate understandability, coding styles should be followed. **Reviewers should check whether a commit is properly formatted before approving!**

* Python: we use the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style, with line width set to 88 characters.
* JavaScript: use of JavaScript should be sparing and with caution. We use the [Google JavaScript Style Guide](https://google.github.io/styleguide/javascriptguide.xml)
* HTML: you can do whatever you want as long as you can explain it 3 days later.

Regardless of the language you are working on, **good documentation is always encouraged**. If you think you won't understand it if you look at it a year later, put a line or two explaining what's going on.

#### Workflow and Review

When starting a new feature, branch off from `master` with a concise but descriptive name, e.g., `templates`. If the branch name contains more than 1 word, it should be delimited by hyphens (`-`), for example, `sku-model`. You are free to develop, commit, and push to new branches whenever you need to.

When you think a feature is completed, submit a Merge Request to the `master` branch on GitLab. (Usually, after pushing to the repo, GitLab will print the link for submitting a Merge Ruquest directly. You can also visit the repo on your browser to submit a new Merge Request.) A Merge Request must be approved by **at least one other person**, before it can be merged into master. When submitting the request, describe your changes in a clear manner, e.g. with a bullet list.

**Reviewers:** if you approve something, you're also responsible for it. So be cool, and don't be afraid to reject a merge request if you see something wrong.