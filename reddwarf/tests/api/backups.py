# Copyright 2011 OpenStack LLC.
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
from proboscis.asserts import assert_equal
from proboscis.asserts import assert_not_equal
from proboscis.asserts import assert_raises
from proboscis import test
from proboscis import SkipTest
from proboscis.decorators import time_out

from reddwarf.tests.util import poll_until
from reddwarf.tests.util import test_config
from reddwarf import tests
from reddwarf.tests import util
from reddwarf.tests.api.instances import WaitForGuestInstallationToFinish
from reddwarf.tests.api.instances import instance_info
from reddwarf.tests.api.instances import GROUP_START
from reddwarf.tests.api.instances import assert_unprocessable

from reddwarfclient import exceptions
# Define groups
GROUP = "dbaas.api.backups"
GROUP_POSITIVE = GROUP + ".positive"
GROUP_NEGATIVE = GROUP + ".negative"
# Define Globals
BACKUP_NAME = 'backup_test'
BACKUP_DESC = 'test description for backup'
backup_info = None
restore_instance_id = None
backup_name = None
backup_desc = None

databases = []
users = []
backup_resp = None


@test(depends_on_classes=[WaitForGuestInstallationToFinish],
      depends_on_groups=[GROUP_START],
      groups=[GROUP])
class BackupsBase(object):
    """
    Base class for Positive and Negative classes for test cases
    """
    def set_up(self):
        self.dbaas = util.create_dbaas_client(instance_info.user)

    def _create_backup(self, backup_name, backup_desc):
        return instance_info.dbaas.backups.create(backup_name,
                                                         instance_info.id,
                                                         backup_desc)
        # print dir(backup_resp)
        # print backup_resp.status
        # print backup_resp.locationRef
        print dir(instance_info)
        print instance_info.dbaas_flavor
        print instance_info.dbaas_flavor_href
        print instance_info.volume
        print instance_info.user.tenant_id

    def _create_restore(self):
        # self.dbaas.instances.create(
        #                     instance_info.name,
        #                     instance_info.dbaas_flavor_href,
        #                     instance_info.volume,
        #                     databases,
        #                     users,
        #                     restorePoint=backup_id)
        #instance_info.dbaas.instances.create(instance_info)
        pass

    @test
    def _list_backups_by_tenant(self):
        pass

    @test
    def _list_backups_by_instance(self):
        pass

    @test
    def _delete_backup(self):
        pass

    @test
    def _get_backup_status(self):
        pass

@test(depends_on_classes=[WaitForGuestInstallationToFinish],
      groups=[GROUP_POSITIVE])
class TestBackupPositive(object):

    @test
    def test_verify_backup(self):
        pass

    @test
    def test_restore_backup(self):
        pass

    @test
    def test_list_backups_for_tenant(self):
        pass

    @test
    def test_list_backups_for_instance(self):
        pass

    @test
    def test_list_backups_for_deleted_instance(self):
        pass

    @test
    def test_get_backup_status_by_id(self):
        pass

    @test
    def test_delete_backup(self):
        pass

@test(depends_on_classes=[WaitForGuestInstallationToFinish],
      groups=[GROUP_NEGATIVE])
class TestBackupNegativeive(object):

    @test
    def test_verify_backup_instance_not_active(self):
        pass

    @test
    def test_restore_deleted_backup(self):
        pass

    @test
    def test_restore_backup_account_not_owned(self):
        pass

    @test
    def test_list_backups_account_not_owned(self):
        pass

    @test
    def test_list_backups_for_instance_another_account(self):
        pass

    @test
    def test_list_backups_for_deleted_instance(self):
        pass

    @test
    def test_delete_deleted_backup(self):
        pass

    @test
    def test_delete_backup_account_not_owned(self):
        pass




@test(depends_on_classes=[WaitForGuestInstallationToFinish],
      groups=[GROUP])
class CreateBackups(object):

    @test
    def test_backup_create_instance_not_found(self):
        """test create backup with unknown instance"""
        assert_raises(exceptions.NotFound, instance_info.dbaas.backups.create,
                      BACKUP_NAME, 'nonexistent_instance', BACKUP_DESC)

    @test
    def test_backup_create_instance(self):
        """test create backup for a given instance"""
        result = instance_info.dbaas.backups.create(BACKUP_NAME,
                                                    instance_info.id,
                                                    BACKUP_DESC)
        print "Instance Info DOT user looks like - "
        print dir(instance_info.user)
        print instance_info.user.tenant_id
        print instance_info.user.tenant
        assert_equal(BACKUP_NAME, result.name)
        assert_equal(BACKUP_DESC, result.description)
        assert_equal(instance_info.id, result.instance_id)
        assert_equal('NEW', result.status)
        instance = instance_info.dbaas.instances.list()[0]
        assert_equal('BACKUP', instance.status)
        global backup_info
        backup_info = result


@test(runs_after=[CreateBackups],
      groups=[GROUP])
class AfterBackupCreation(object):

    @test
    def test_instance_action_right_after_backup_create(self):
        """test any instance action while backup is running"""
        assert_unprocessable(instance_info.dbaas.instances.resize_instance,
                             instance_info.id, 1)

    @test
    def test_backup_create_another_backup_running(self):
        """test create backup when another backup is running"""
        assert_unprocessable(instance_info.dbaas.backups.create,
                             'backup_test2', instance_info.id,
                             'test description2')

    @test
    def test_backup_delete_still_running(self):
        """test delete backup when it is running"""
        result = instance_info.dbaas.backups.list()
        backup = result[0]
        assert_unprocessable(instance_info.dbaas.backups.delete, backup.id)


@test(runs_after=[AfterBackupCreation],
      groups=[GROUP])
class WaitForBackupCreateToFinish(object):
    """
        Wait until the backup create is finished.
    """

    @test
    @time_out(60 * 30)
    def test_backup_created(self):
        # This version just checks the REST API status.
        def result_is_active():
            backup = instance_info.dbaas.backups.get(backup_info.id)
            if backup.status == "COMPLETED":
                return True
            else:
                assert_not_equal("FAILED", backup.status)
                return False

        poll_until(result_is_active)


@test(depends_on=[WaitForBackupCreateToFinish],
      groups=[GROUP])
class ListBackups(object):

    @test
    def test_backup_list(self):
        """test list backups"""
        result = instance_info.dbaas.backups.list()
        assert_equal(1, len(result))
        backup = result[0]
        assert_equal(BACKUP_NAME, backup.name)
        assert_equal(BACKUP_DESC, backup.description)
        assert_equal(instance_info.id, backup.instance_id)
        assert_equal('COMPLETED', backup.status)

    @test
    def test_backup_list_for_instance(self):
        """test list backups"""
        result = instance_info.dbaas.instances.backups(instance_info.id)
        assert_equal(1, len(result))
        backup = result[0]
        assert_equal(BACKUP_NAME, backup.name)
        assert_equal(BACKUP_DESC, backup.description)
        assert_equal(instance_info.id, backup.instance_id)
        assert_equal('COMPLETED', backup.status)

    @test
    def test_backup_get(self):
        """test get backup"""
        backup = instance_info.dbaas.backups.get(backup_info.id)
        assert_equal(backup_info.id, backup.id)
        assert_equal(backup_info.name, backup.name)
        assert_equal(backup_info.description, backup.description)
        assert_equal(instance_info.id, backup.instance_id)
        assert_equal('COMPLETED', backup.status)


@test(runs_after=[ListBackups],
      groups=[GROUP])
class RestoreUsingBackup(object):

    @test
    def test_restore(self):
        """test restore"""
        if test_config.auth_strategy == "fake":
            raise SkipTest("Skipping restore tests for fake mode.")
        restorePoint = {"backupRef": backup_info.id}
        result = instance_info.dbaas.instances.create(
            instance_info.name + "_restore",
            instance_info.dbaas_flavor_href,
            instance_info.volume,
            restorePoint=restorePoint)
        assert_equal(200, instance_info.dbaas.last_http_code)
        assert_equal("BUILD", result.status)
        global restore_instance_id
        restore_instance_id = result.id


@test(depends_on_classes=[RestoreUsingBackup],
      runs_after=[RestoreUsingBackup],
      groups=[GROUP])
class WaitForRestoreToFinish(object):
    """
        Wait until the instance is finished restoring.
    """

    @test
    @time_out(60 * 32)
    def test_instance_restored(self):
        if test_config.auth_strategy == "fake":
            raise SkipTest("Skipping restore tests for fake mode.")

        # This version just checks the REST API status.
        def result_is_active():
            instance = instance_info.dbaas.instances.get(restore_instance_id)
            if instance.status == "ACTIVE":
                return True
            else:
                # If its not ACTIVE, anything but BUILD must be
                # an error.
                assert_equal("BUILD", instance.status)
                if instance_info.volume is not None:
                    assert_equal(instance.volume.get('used', None), None)
                return False

        poll_until(result_is_active)


@test(runs_after=[WaitForRestoreToFinish],
      groups=[GROUP])
class DeleteBackups(object):

    @test
    def test_backup_delete_not_found(self):
        """test delete unknown backup"""
        assert_raises(exceptions.NotFound, instance_info.dbaas.backups.delete,
                      'nonexistent_backup')

    @test
    @time_out(60 * 2)
    def test_backup_delete(self):
        """test delete"""
        instance_info.dbaas.backups.delete(backup_info.id)
        assert_equal(202, instance_info.dbaas.last_http_code)

        def backup_is_gone():
            result = instance_info.dbaas.instances.backups(instance_info.id)
            if len(result) == 0:
                return True
            else:
                return False
        poll_until(backup_is_gone)
        assert_raises(exceptions.NotFound, instance_info.dbaas.backups.get,
                      backup_info.id)
