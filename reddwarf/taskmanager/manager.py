# vim: tabstop=4 shiftwidth=4 softtabstop=4

# Copyright 2011 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from reddwarf.common import exception
from reddwarf.openstack.common import log as logging
from reddwarf.openstack.common import periodic_task
from reddwarf.taskmanager import models
from reddwarf.taskmanager.models import FreshInstanceTasks

LOG = logging.getLogger(__name__)
RPC_API_VERSION = "1.0"


class Manager(periodic_task.PeriodicTasks):

    def resize_volume(self, context, instance_id, new_size):
        instance_tasks = models.BuiltInstanceTasks.load(context, instance_id)
        instance_tasks.resize_volume(new_size)

    def resize_flavor(self, context, instance_id, new_flavor_id,
                      old_memory_size, new_memory_size):
        instance_tasks = models.BuiltInstanceTasks.load(context, instance_id)
        instance_tasks.resize_flavor(new_flavor_id, old_memory_size,
                                     new_memory_size)

    def reboot(self, context, instance_id):
        instance_tasks = models.BuiltInstanceTasks.load(context, instance_id)
        instance_tasks.reboot()

    def restart(self, context, instance_id):
        instance_tasks = models.BuiltInstanceTasks.load(context, instance_id)
        instance_tasks.restart()

    def migrate(self, context, instance_id):
        instance_tasks = models.BuiltInstanceTasks.load(context, instance_id)
        instance_tasks.migrate()

    def delete_instance(self, context, instance_id):
        try:
            instance_tasks = models.BuiltInstanceTasks.load(context,
                                                            instance_id)
            instance_tasks.delete_async()
        except exception.UnprocessableEntity as upe:
            instance_tasks = models.FreshInstanceTasks.load(context,
                                                            instance_id)
            instance_tasks.delete_async()

    def delete_backup(self, context, backup_id):
        models.BackupTasks.delete_backup(context, backup_id)

    def create_backup(self, context, backup_id, instance_id):
        instance_tasks = models.BuiltInstanceTasks.load(context, instance_id)
        instance_tasks.create_backup(backup_id)

    def create_instance(self, context, instance_id, name, flavor_id,
                        flavor_ram, image_id, databases, users, service_type,
                        volume_size, security_groups, backup_id):
        instance_tasks = FreshInstanceTasks.load(context, instance_id)
        instance_tasks.create_instance(flavor_id, flavor_ram, image_id,
                                       databases, users, service_type,
                                       volume_size, security_groups,
                                       backup_id)
