# HypoMeals
[![pipeline status](https://gitlab.oit.duke.edu/hypomeals/hypomeals/badges/master/pipeline.svg)](https://gitlab.oit.duke.edu/hypomeals/hypomeals/commits/master)

HypoMeals is a sophisticated food manufacturing management software. It features SKU and ingredients managment, product lines, and much more.

### Prerequisites

* [Docker Commmunity Edition](https://hub.docker.com/search/?type=edition&offering=community)
* [Docker Compose 1.8](https://docs.docker.com/compose/install/) or above. Depending on the host OS, this may or may not be bundled with Docker.
* [Python 3.7](https://www.python.org/) or above
* [Git](https://git-scm.com/)
* [Redis](https://redis.io/download)
* (Optional) [PyCharm Professional](https://www.jetbrains.com/pycharm/)

### Architecture

This project is built with [Django](https://www.djangoproject.com/), using the default ORM and template engine. If you haven't already, read the [official tutorials](https://docs.djangoproject.com/en/2.1/intro/) first.

The Django project is comprised on one "app": a Django term for a unit of executable code. The project itself lives under a subdirectory called `hypomeals`.

#### Models

Since we are using the Django ORM, the models are automatically managed by Django for us. There are several main models, as described below.

##### SKU

The `Sku` model represents, unsurprisingly, the SKUs. To conserve space, several fields are defined as `ForeingKey`s: the UPC numbers, and the Product Line. They can be retrieved / queried upon using the double underscore syntax provided by the Django ORM.

The `Sku` model also has a many-to-many relationship with `Ingredient`, through the `SkuIngredient` relation table. This relation is also known as "Formula".

Its primary key is `number`, corresponding to "SKU#", which can be autogenerated if one is not provided. 

The `__str__` and `__repr__` methods are overriden to reflect the standard display format for SKUs.

**Note: ** this model overrides the default `save()` method to supply a number if the user did not provide one. The number will be 1 plus the maximum number currently in the database.

##### Ingredient

The `Ingredient` model, similarly, represents the ingredients. The `vendor` field is defined as a `ForeignKey` for extensibility purposes: if in the future, a vendor has more attributes than just `info`, the cost of changing this model that would be much lower, than if `vendor` were a `CharField` in the model.

**Note:** similar to `Sku`, this model also overrides the default `save()` method to supply a number if a user did not provide one.

##### Formula

This model represents a formula. The formula's ingredients are recorded in a separate model called `FormulaIngredient`.

##### Goal

This model represents a goal. The goal's items are represented in a separate model called `GoalItem`. The items, if scheduled, will map to a `GoalSchedule`.

##### Sale

This model represents a sale to a customer. It contains a foreign-key relationship with the `Customer` model, and records the year, week, quantity of sales.

#### Permission and Authentication

The project uses Django's built-in authentication system, with a custom user model (defined in `models.py` as `User`). Initially all users are added to the `Users` group, which only grants permission to view all objects (i.e., instances of models). A user can also be added to an `Admins` group, which is allowed to add, change, delete, and view all objects.

Permission checking is done by the `@auth.user_is_admin` decorator, which checks whether the user belongs to the `Admins` group, or is a `superuser` (in Django's term). Finer grain permission control may be implemented in the future.

Users without the required permission to access a particular resource will be redirected to the `403.html` page, where an error message is displayed. If the request was an AJAX one, a `JsonResponse` containing the error message is returned.

#### File Layout

The files are generally laid out according to Django's conventions: `models.py`, `urls.py`, etc., are all where they are supposed to be. However, for clarity's sake, there are a few changes to the standard Django directory layout, as described below:

##### Views

With dozens of webpages, a singular `views.py` quickly becomes too cluttered to browse. As a result, the views are moved into a Python package named `views`, separated in different Python source files named appropriately. The `views/__init__.py` then imports these separate views from their respective source files, and consolidates them under the root of the package, so that in `urls.py`, one can still write the familiar `views.<view_name>` syntax and everything still works as expected.

##### `bulk_export.py`

This file contains the general functions and data structures needed to generated CSV files from a given set of data.

##### `bulk_import.py` and `importers.py`

These two files work in tandem to parse, process, and import CSV formatted data supplied by user. The former defines the main driving logic, while the latter defines the detailed parsing logic.

Parsing of the CSV files are done by the standard library `csv` module. However, the generation of model instances and committance to database are highly automated, and heavily based on existing model structure.

##### `exceptions.py`

This file defines some custom exceptions that convey specific meanings. For example, a `DuplicateException` may be raised during the processing of one of the input files to both rollback all database changes and to contain enough information such that the user can fix the error.

##### `utils.py`

This file contains some helpful utility functions, decorators, and helper classes. For example, the `@parameterized` meta-decorator is defined in this file.

##### `auth.py`

This file defines some utility functions / decorators related to authentication and permission checking. For example, the `@permission_required_ajax` decorator is defined in this file.

##### `sales.py`

This file contains code for the Sales subsystem that interfaces with the company's sales interface.

#### Logs

We heavily configured the various loggers used by Django to maximize the information provided for debugging purposes. **The use of `print` statements are therefore discouraged**. Check out `hypomeals/HypoMeals/settings.py` to see how the logs are configured. 

If you are using Docker to deploy the application, logs of Nginx (the reverse proxy) and 

#### Celery and Redis

Part of the project involves the use of asynchronous tasks, such as the ones to fetch sales records from a web interface separate from this system. Such tasks, due to their time-consuming nature, cannot be run within the Django process without severely degrading the user's experience.

As a result, the Celery project is integrated into the system to provide distributive, asynchronous execution of "tasks" that are unsuitable for execution within the Django process. Refer to the [Celery project's user guide](http://docs.celeryproject.org/en/latest/userguide) for more information on the project.

On a high level, Django and Celery runs side-by-side as two processes. They communicate through [Redis](https://redis.io) as a message broker. Code in Django does not invoke Celery functions directly, but rather sends a message to a specified channel in Redis. This message is then picked up by a Celery dispatcher, again, running as a separate process, and executed in one of the workers.

The Celery worker, although distinct from the main Django process, has access to the same database (and therefore ORM) of the main Django project, allowing seemless operation on the Django side.

Additionally, yet another separate process, called Celery Beat, runs a scheduler service based on Django's database system as a backend, to periodically run a set of tasks at specified times, for example, to refresh daily sales records for the current year as they update.

### Code Style

Several languages are used throughout the project. To facilitate understandability, coding styles should be followed. **Reviewers should check whether a commit is properly formatted before approving!**

- Python: we use the [PEP 8](https://www.python.org/dev/peps/pep-0008/) style, with line width set to 88 characters.
- JavaScript: use of JavaScript should be sparing and with caution. We use the [Google JavaScript Style Guide](https://google.github.io/styleguide/javascriptguide.xml)
- HTML: you can do whatever you want as long as you can explain it 3 days later.

Regardless of the language you are working on, **good documentation is always encouraged**. If you think you won't understand it if you look at it a year later, put a line or two explaining what's going on.

#### Workflow and Review

When starting a new feature, branch off from `master` with a concise but descriptive name, e.g., `templates`. If the branch name contains more than 1 word, it should be delimited by hyphens (`-`), for example, `sku-model`. You are free to develop, commit, and push to new branches whenever you need to.

When you think a feature is completed, submit a Merge Request to the `master` branch on GitLab. (Usually, after pushing to the repo, GitLab will print the link for submitting a Merge Ruquest directly. You can also visit the repo on your browser to submit a new Merge Request.) A Merge Request must be approved by **at least one other person**, before it can be merged into master. When submitting the request, describe your changes in a clear manner, e.g. with a bullet list.

**Reviewers:** if you approve something, you're also responsible for it. So be cool, and don't be afraid to reject a merge request if you see something wrong.

### Optional Dependencies

The system has several optional dependencies. Without these dependencies, some features in the project cannot be enabled, but the overall functionality of the application remains present.

#### Credentials

This project integrates with various other systems, and as a result, may require separate credentials that may not be version-controlled. These credentials should all be stored under the `credentials/` directory. The following subsections discuss the details of each kind of credentials found in this directory.

##### HTTPS Certificates

The project uses the HTTPS protocol. For security reasons, the certificates and private keys are not included in the repository. **They must be obtained separately before running the project.** The certificates are distributed in a file named `certs.zip`: all of the files in this archive must be placed under the `credentials/` directory.

**Note:** the certificates are self-issued, which means most modern browsers will warn you that the certificate is not trusted. This is fine, and the warning should be dismissed.

However, the certificates are issued with an extension called `Subject Alternative Name`s, and will certify three hosts: `vcm-4081.vm.duke.edu` (the production server), `127.0.0.1` and `localhost`. What that means is that, although your browser may warn about untrusted issuer, it **should not** warn about an invalid common name, if the project is being deployed locally.

##### Changing the domain name

If you wish to deploy on a different server with a different domain name, you will need to provide your own certificates. 

First, place the certificates in the `credentials/` directory. Then, you will need to edit the file `nginx/config/web-app.conf` and point the `ssl_certificate` and `ssl_certificate_key` parameters to the correct filenames.

**Note:** the `credentials/` directory is automatically mapped to the correct location (`/etc/nginx/certs/`) in the Docker container, with read-only permissions.

##### OAuth

The system uses OAuth to interface with Duke's NetID authentication service to support Single Sign-On. For security purposes, a file, called `oauth_config.json` that contains all the OAuth secrets and configurations, must be obtained separately, and placed under the `credentials/` directory. If this file is absent, Single Sign-On will be disabled.

#### Google Cloud Services

The system uses Google Cloud Services for storage of user-uploaded static files (e.g. images). For security purposes, a clients secret file that contains the service account information of the project must be obtained separated, and placed under Django's base directory, for this support to be enabled.

### Getting Started

To get started, first clone the repository onto your computer

```bash
git clone git@gitlab.oit.duke.edu:hypomeals/hypomeals.git
cd hypomeals
```

There are then two ways of running the project for development:

#### Virtual Environment (Recommended)

A virtual environment may be much better suited for development, because some IDEs can automatically detect and run the Django project, if the environment is set up correctly. To set up a new virtual environment on a Unix host, use these commands under the root directory of the project:

```bash
# This will set up a fresh environment under a directory named venv/
$ python -m venv venv/
# This will "activate" the new virtual environment
$ source venv/bin/activate
```

For tutorials and guides on setting up virtual environments on other OSes, check the [official documentation](https://docs.python.org/3/library/venv.html#module-venv).

Once the virtual environment is activated, install all project requirements:

```bash
$ pip install -r hypomeals/requirements.txt
```

Then, two dependent services, Redis and Celery, must be run. **Note** that this step may be replaced by running them both in Docker as discussed in the next section.

```bash
$ cd hypomeals/  # This is the Django base directory
$ redis-server
$ celery -A HypoMeals worker -l info
# Optionally, run the Celery Beat scheduler
$ celery -A HypoMeals beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

After this, an environment variable must be set to choose a database to connect to. Refer to the "Configuration Options" section for more details. For now, simply point it to any PostgreSQL instance.

Finally, to start the Django development server, use the command:

```bash
$ cd hypomeals/
$ python manage.py migrate
$ python manage.py runserver 8000
```

Finally, to see the website, go to `http://127.0.0.1:8000` on your browser. 

#### Docker

The project is designed to be deployed by a Docker engine. A `docker-compose.yml` is provided so that the containers may be spun up easily all at once. In the root directory of the project, simply type

```bash
sudo docker-compose up
```

**Note:** `sudo` may not be required on Windows or macOS computers.

Once the containers are all set up, visit `https://127.0.0.1` on your host computer. Due to restrictions on Docker containers, it is not possible to set up automatic protocol upgrade to SSL. You must therefore enter `https:` as the scheme explicitly.

##### Running individual services with Docker

Individual services may also be run using Docker, either for testing purposes or for developmental support. For example, to start only Redis and Celery / Celery Beat services, use the command:

```bash
$ sudo docker-compose up -d redis celery-beat
```

After this, a Django instance running in a virtual environment native to the OS will be able to leverage these services, without having to run them separately.

### System Administration

As a fully-featured, sophisticated inventory and business insights system, HypoMeals is robust but highly configurable. This section discusses the procedures a sysadmin may use to administer this system.

#### Configuration Options

The project supports various configuration options, through the use of environment variables. For virtual environments, simply set environment variables with the `export` command, if you are using a Unix-based shell. For Windows, [here](https://docs.microsoft.com/en-us/powershell/module/microsoft.powershell.core/about/about_environment_variables?view=powershell-6) is a tutorial for setting environment variables in PowerShell. For Docker users, a set of environment variables are provided via the files `web-vars.env` and `web-vars-prod.env`, for developer and production uses, respectively.

The following configuration options are available:

##### Database

* `DJANGO_DB_HOST`: the hostname of a PostgreSQL database. Default: `vcm-4081.vm.duke.edu`
* `DJANGO_DB_PORT`: the port for a PostgreSQL database. Default: 5432
* `DJANGO_USE_LOCAL_DB`: a legacy option. If set to 1, equivalent to `DJANGO_DB_HOST=localhost`

##### Email

* `DJANGO_EMAIL_HOST`: the hostname of an SMTP server. Default: `smtp.mailgun.org`
* `DJANGO_EMAIL_PORT`: the port to an SMTP server. Default: 587
* `DJANGO_EMAIL_USE_TLS`: if 1, will try to use a TLS connection when connecting to the SMTP server. Default: 1
* `DJANGO_EMAIL_USER`: the username to the SMTP server. Default: empty
* `DJANGO_EMAIL_PASSWORD`: the password to the SMTP server. Default: empty
* `DJANGO_EMAIL_FROM`: the "From" field of an Email. Default: `webmaster@localhost`

##### Celery

* `CELERY_REDIS_HOST`: the hostname of a Redis server. Default: `localhost`
* `CELERY_REDIS_PORT`: the port of a Redis server. Default: 6379

##### Other

* `HOSTNAME`: the hostname of the server the system is running on. Default: `vcm-4081.vm.duke.edu`.

#### Backup

To ensure resilience against failures and disasters, the system is equipped with a full backup service. Every day at 1 AM, the backup service runs automatically, taking a full database snapshot, and storing it in Google Cloud Storage. The credentials used by the backup system is read-write-only: this ensures that even if the admin account is compromised, the backups cannot be deleted from the storage service. The backup service sends an email to notify the administrator that the backup has been completed successfully.

Backups will be named after the time that the backup service starts running. For example, a backup taken at 1:00 AM, March 24, 2019 will be named

```
backup-2019-03-24T01:00:<seconds>.<microseconds>  # (micro)seconds might vary
```

A separate service, with a separate credential, is run alongside the main backup service, to rotate the backups. By default, 7 daily backups, 4 weekly backups, and 12 monthly backups are retained, in which the 8th daily backup is automatically promoted to a weekly backup, the 5th weekly backup to a monthly backup, and the 13th month backup is deleted.

To take a backup, a backup job must be set up as a "Periodic task" in the system in the admin panel. The task's name will be `meals.tasks.backup_all`. This task will have a cron specifier of "0 1 * * *" such that it runs at 1 AM every day. This task doesn't require any arguments to run, and should remain in the "Enabled" status.

##### Taking a backup manually

To take a manual backup, simply create another `meals.tasks.backup_all` task and set it to run every second. Then, check the box to mark it as a "One-off task", such that it is disabled automatically after running once.

Note that a backup taken manually will count towards the staggered retention discussed above.

##### Restoring from a backup

To restore from a database backup, an administrator must first download the desired backup from Google Cloud Storage, onto the server running HypoMeals. This can be done either via the [web interface](https://console.cloud.google.com/storage/browser?project=hypomeals), or using the `gsutil` command. Once the file is downloaded, issue the following command in the project base directory:

```bash
$ sudo docker-compose -f docker-compose-prod.yml exec -T -u postgres db psql < /path/to/backup/file
```

Backups may be restored without introducing additional downtime to the server.