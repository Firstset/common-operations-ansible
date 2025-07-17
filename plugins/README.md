# Collections Plugins Directory

## firstset.common_operations.report

This plugin generates a nice HTML report page for the check fleet task. In order to use this plugin, you need to install the following Python packages (assuming you have already installed Ansible):

```
pip install humanize pandas
```

Create or modify the `ansible.cfg` file in your Ansible project directory to include the plugin:

```ini
[defaults]
callbacks_enabled = firstset.common_operations.report # comma separated list of plugins
```

After enabling the plugin, when you executed the check fleet tasks in the `common` role, an enhanced report will be generated and opened by the default browser.
