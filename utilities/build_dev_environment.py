from __future__ import with_statement
import os
import urllib
import shutil
import zipfile
import re
import sys
from fabric.api import *
import os.path as op

#########################################
# Downloads a Virgo server and the OpenWorm
# bundles, compiles using Maven & deploys in Virgo
# by: Stephen Larson (stephen@openworm.org)
#     & Padraig Gleeson (p.gleeson@gmail.com)
#
# To use:
# * Make sure Maven (http://maven.apache.org) is installed
# * Make sure Fabric is installed:
#   http://docs.fabfile.org/en/1.5/installation.html
# * Set JAVA_HOME and MAVEN_HOME directories below:

os.environ['JAVA_HOME'] = '/usr'
os.environ['MAVEN_HOME'] = '/usr'

# Set the location to create the development environment
repository_dir = op.join(os.environ['HOME'], 'openworm_dev')

# Set the prteferred method for cloning from GitHub
#github_pref = "HTTP"
github_pref = "SSH"
#github_pref = "Git Read-Only"


#######################################

#check to make sure Maven is pointed to appropriately
try:
   with open(op.join(os.environ['MAVEN_HOME'], 'bin/mvn')) as f: pass
except IOError as e:
   sys.exit("Can't find mvn under " + os.environ['MAVEN_HOME'] + "-- is MAVEN_HOME set appropriately?")

openwormpackages = ['org.openworm.simulationengine.core',
'org.openworm.simulationengine.samplesolver',
'org.openworm.simulationengine.samplesimulator',
'org.openworm.simulationengine.samplesimulation',
'org.openworm.simulationengine.model.sph',
'org.openworm.simulationengine.solver.sph',
'org.openworm.simulationengine.simulator.sph',
'org.openworm.simulationengine.simulation',
'org.openworm.simulationengine.frontend',
'org.openworm.simulationengine']

pre={}
pre["HTTP"]="https://github.com/openworm/"
pre["SSH"]="git@github.com:openworm/"
pre["Git Read-Only"]="git://github.com/openworm/"

repos = []
for p in openwormpackages:
    repos = repos + [pre[github_pref] + p + '.git']


if not op.isdir(repository_dir):
    print "Creating a new directory: "+repository_dir
    os.mkdir(repository_dir)

virgo_version = "3.6.0.RELEASE"
virgo_zip = "http://www.eclipse.org/downloads/download.php?file=/virgo/release/VP/%s/virgo-tomcat-server-%s.zip&r=1"%(virgo_version, virgo_version)

virgo_dir = op.join(repository_dir, "virgo-tomcat-server-"+virgo_version)
if not op.isdir(virgo_dir):
    print "Downloading: %s and unzipping into %s..."%(virgo_zip,repository_dir)
    (zFile, x) = urllib.urlretrieve(virgo_zip)
    vz = zipfile.ZipFile(zFile)
    vz.extractall(repository_dir)
    os.remove(zFile)
else:
    print "Keeping existing Virgo install in "+virgo_dir

os.environ['SERVER_HOME'] = virgo_dir

for owp in openwormpackages:
    with lcd(repository_dir):
        print
        if not op.isdir(op.join(repository_dir, owp)):
            print "Cloning repository %s into %s"%(owp, repository_dir)
            repo = pre[github_pref] + owp + '.git'
            print local('git clone %s'%repo, capture=True)
        else:
            print "Using existing repository %s in %s"%(owp, repository_dir)
            with lcd(op.join(repository_dir, owp)):
                print local('git pull', capture=True)

        with lcd(op.join(repository_dir, owp)):
            print local('$MAVEN_HOME/bin/mvn install', capture=True)
            if op.isdir(op.join(repository_dir, owp+"/target/classes/lib/")):   # Probably not platform indep...
                print local('cp target/classes/lib/* $SERVER_HOME/repository/usr/', capture=True)
            print local('pwd', capture=True)

            with settings(hide('everything'), warn_only=True):
                print local('cp target/*.*ar $SERVER_HOME/repository/usr/', capture=True)


#put the .plan file in the pickup folder
with lcd(op.join(repository_dir, 'org.openworm.simulationengine')):
    print local('cp owsefull.plan $SERVER_HOME/pickup/', capture=True)


#fix the properties file
f = open(op.join(virgo_dir, 'repository/ext/org.eclipse.virgo.web.properties'), 'r+')
text = f.read()
text = re.sub('strict', 'defaulted', text)
f.seek(0)
f.write(text)
f.truncate()
f.close()

#set permissions on the bin directory
#these do carry over into the archive
with lcd(virgo_dir):
    print local('chmod -R +x ./bin', capture=True)


print 'Your local development environment is ready at: ' + repository_dir