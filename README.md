# FoldAtlas

FoldAtlas is a repository of genome-wide RNA structure probing data.  
The repository is described in detail [here](https://doi.org/10.1093/bioinformatics/btw611).

The live site is available at [foldatlas](http://www.foldatlas.com)

## Installing locally

- On macOS or Linux
- Install the latest versions of:
  - [Virtualbox download](https://www.virtualbox.org/wiki/Downloads)
  - [Vagrant download](https://www.vagrantup.com/)
  - [Ansible download](http://docs.ansible.com/ansible/latest/intro_installation.html)
  (more information at [Ansible](https://www.ansible.com/))
- Clone this code repository
- Create a python v3.4 environment (using conda or virtualenv)  
  The `requirements.txt` file lists the python packages required for development.  
  Packages required for production are indicated and are mirrored in the 
  provisioning scripts 
 
## Setting up a local FoldAtlas

To initialise the local database with the current live database, set `foldatlas_load_sql_dump: "yes"`
in the `provisioning/vars.yml` file.  
Run `vagrant up` in the same folder as this file.    
The first `vagrant up` call will install and configure the required components.  
The webserver address is `http://localhost:8080`.

Set `foldatlas_load_sql_dump: "no"` in the `provisioning/vars.yml` file.  
Subsequent calls to `vagrant up` will check each component is the latest and start the webserver.



## Tested on MacOSX







