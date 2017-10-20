# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
    #config.vm.box = "ubuntu/trusty64"
    config.vm.box = "centos/7"

    config.vm.provider "virtualbox" do |vb|
        vb.name = "vagrant-foldatlas-dev"
        vb.memory = "8192"
        vb.cpus = 3
    end

    # config.vm.synced_folder "/media/shares/Research-Groups/Yiliang-Ding/data_analysis_Ding_2013/MAC/#Yin/Mapping_F/raw_data/structures", "/vagrant/structure_data"

    config.ssh.forward_agent = true
    config.ssh.forward_x11 = true

    config.vm.network :forwarded_port, guest: 80, host: 8080

#    config.vm.provision "machine", type: "ansible" do |ansible|
#        ansible.playbook = "provisioning/playbook-machine.yml"
#    end

#    config.vm.provision "fa_db", type: "ansible" do |ansible|
#        ansible.playbook = "provisioning/playbook-foldatlas-db.yml"
#    end

#    config.vm.provision "fa_web", type: "ansible" do |ansible|
#        ansible.playbook = "provisioning/playbook-foldatlas-web.yml"
#    end

    config.vm.provision "ansible" do |ansible|
        ansible.playbook = "provisioning/playbook.yml"
    end
end
