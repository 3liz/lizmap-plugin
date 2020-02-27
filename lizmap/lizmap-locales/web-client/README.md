
It is not recommended to modify by hand, `po` and `pot` files into `web-client/`!

We prefer to translate strings with Transifex, and then import translations
into Lizmap.

pot files must be generated directly from Lizmap properties files.


Be sure you have installed Transifex cli, but also PHP-cli and its mbstring extension
(`apt-get install php7.2-mbstring`).

You also need to retrieve the source code of lizmap, and download some PHP packages
with Composer.

```
git clone https://github.com/3liz/lizmap-web-client.git
cd lizmap-web-client 
composer install
```


Updating the list of strings to translate (pot files)
-----------------------------------------------------

First, you must generate the `.pot` files, from the `.properties` files.

To do it, be sure that you don't have uncommitted changes into your lizmap-web-client
repository, because the following script will checkout the branch
corresponding to the current branch of lizmap-locales.

Then you have to execute this command from the web_client directory, by giving the 
path to the `lizmap-web-client/lizmap/` directory:

```
cd web-client/
./update_from_lizmap.sh /path/to/lizmap-web-client/lizmap/
```

Then you push them to Transifex

```
./push_to_transifex.sh
```


Updating translated strings
---------------------------

When some new translations are available in Transifex, you can import them
into Lizmap.

First retrieve translated string from Transifex, it updates po files:

```
./update_from_transifex.sh
```

Then be sure that you don't have uncommitted changes into your lizmap-web-client
repository, because the following script will checkout the branch
corresponding to the current branch of lizmap-locales.

Then execute this script:

```
./push_to_lizmap.sh /path/to/lizmap-web-client/lizmap/
```

It updates `.properties` files  into lizmap-web-client from `po` files. You can
then commit updated files into lizmap-web-client.
