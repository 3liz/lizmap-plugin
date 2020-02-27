
It is not recommended to modify by hand, `ts` files into `plugin/`!
We prefer to translate strings with Transifex, and then translation are imported
into Lizmap plugin.

## Using the makefile in Lizmap QGIS plugin

From Lizmap plugin:
```bash
# Prepare TS files
make i18n_1_prepare

# Push to Transifex
make i18n_2_push

# Pull from Transifex
make i18n_3_pull

# Compile TS fiels to QM files.
make i18n_4_compile
```

## Manually

### Updating the list of strings to translate for Lizmap plugin

You push it to Transifex:

```
tx push -s
```


### Updating translated strings

When some new translations are available in Transifex, you can import them.

First retrieve translated string from Transifex:

```
tx pull
```
