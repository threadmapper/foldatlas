# -*- mode: ruby -*-
# vi: set ft=ruby :

Vagrant.configure(2) do |config|
    #config.vm.box = "ubuntu/trusty64"
    config.vm.box = "centos/7"
  
    config.vm.provider "virtualbox" do |vb|
        vb.memory = "8192"
    end

#    config.vm.provider "virtualbox" do |v|

        # config.vm.synced_folder "/media/shares/Research-Groups/Yiliang-Ding/data_analysis_Ding_2013/MAC/#Yin/Mapping_F/raw_data/structures", "/vagrant/structure_data"
    
        config.ssh.forward_agent = true
        config.ssh.forward_x11 = true
        config.vm.network :forwarded_port, guest: 80, host: 8080
#    end

    config.vm.provision "ansible" do |ansible|
        #ansible.playbook = "provisioning/playbook.ubuntu.yml"
        ansible.playbook = "provisioning/playbook.centos.yml"
    end
        

end
