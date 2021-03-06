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
from reddwarfclient import backups
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
    #def set_up(self):
    def __init__(self):
        self.status = None
        self.backup_id = None
        self.dbaas = util.create_dbaas_client(instance_info.user)

    def _create_backup(self, backup_name, backup_desc):
        backup_resp = instance_info.dbaas.backups.create(backup_name,
                                                         instance_info.id,
                                                         backup_desc)
        return backup_resp

    def _create_restore(self):
        restorePoint = {"backupRef": backup_resp.id}
        restore_resp = instance_info.dbaas.instances.create(
                instance_info.name + "_restore",
                instance_info.dbaas_flavor_href,
                instance_info.volume,
                restorePoint=restorePoint)
        return restore_resp

    def _list_backups(self):
        return instance_info.dbaas.backups.list()

    def _list_backups_by_instance(self):
        return instance_info.dbaas.instances.backups(instance_info.id)

    def _delete_backup(self, backup_id):
        return instance_info.dbaas.backups.delete(backup_id)

    def _get_backup_status(self, backup_id):
        return instance_info.dbaas.backups.get(backup_id).status

    def _verify_instance_is_active(self):
        result = instance_info.dbaas.instances.get(instance_info.id)
        print result.status
        return result.status == 'ACTIVE'

    def _verify_instance_status(self, instance_id, status):
        resp = instance_info.dbaas.instances.get(instance_id)
        return resp.status == status

    def _verify_backup_status(self, backupid, status):
        resp = instance_info.dbaas.backups.get(backupid)
        return resp.status == status


@test(depends_on_classes=[WaitForGuestInstallationToFinish],
      groups=[GROUP_POSITIVE])
class TestBackupPositive(BackupsBase):

    @test
    def test_verify_backup(self):
        result = self._create_backup(BACKUP_NAME, BACKUP_DESC)
        assert_equal(BACKUP_NAME, result.name)
        assert_equal(BACKUP_DESC, result.description)
        assert_equal(instance_info.id, result.instance_id)
        assert_equal('NEW', result.status)
        instance = instance_info.dbaas.instances.list()[0]
        assert_equal('BACKUP', instance.status)
        self.backup_id = result.id
        # global backup_info
        # backup_info = result
        # print dir(backup_info)
        # print dir(backup_info.id)
        # print backup_info.id
        # print backup_info.locationRef
        # Timing necessary to make the error occur
        #poll_until(self._verify_instance_is_active, time_out=120,
        #           sleep_time=1)
        print "Polling starts"
        poll_until(lambda: self._verify_backup_status(self.backup_id, "NEW"),
                   time_out=120, sleep_time=1)
        print "After First Polling"
        poll_until(lambda: self._verify_instance_status(instance_info.id,
                   "BACKUP"), time_out=120, sleep_time=1)
        print "After second Polling"
        # poll_until(lambda: self._verify_backup_status(self.backup_id,
        #             "BUILDING"), time_out=120, sleep_time=1)
        print "After third Polling"
        poll_until(lambda: self._verify_backup_status(self.backup_id,
                    "COMPLETED"), time_out=120, sleep_time=1)
        print "After fourth Polling"
        poll_until(lambda: self._verify_instance_status(instance_info.id,
                    "ACTIVE"), time_out=120, sleep_time=1)
        # poll_until(self._verify_instance_is_active, time_out=120,
        #            sleep_time=1)
        print "After fifth Polling"

    @test
    def test_restore_backup(self):
        if test_config.auth_strategy == "fake":
            raise SkipTest("Skipping restore tests for fake mode.")
        restore_result = self._create_restore()
        assert_equal(200, instance_info.dbaas.last_http_code)
        assert_equal("BUILD", restore_result.status)
        global restore_info
        restore_info = restore_result
        global restore_instance_id
        restore_instance_id = restore_result.id
        #print dir(restore_info)

    @test(runs_after=[test_verify_backup])
    def test_list_backups(self):
        result = self._list_backups()
        assert_equal(1, len(result))
        backup = result[0]
        assert_equal(BACKUP_NAME, backup.name)
        assert_equal(BACKUP_DESC, backup.description)
        assert_equal(instance_info.id, backup.instance_id)
        #assert_equal('COMPLETED', backup.status)
        #print backup.status

    @test(runs_after=[test_verify_backup])
    def test_list_backups_for_instance(self):
        result = self._list_backups_by_instance()
        assert_equal(1, len(result))
        result = result[0]
        assert_equal(BACKUP_NAME, result.name)
        assert_equal(BACKUP_DESC, result.description)
        assert_equal(instance_info.id, result.instance_id)


    @test
    def test_list_backups_for_deleted_instance(self):
        pass

    @test
    def test_get_backup_status_by_id(self):
        pass

    @test(runs_after=[test_verify_backup, test_list_backups,
                      test_list_backups_for_instance])
    def test_delete_backup(self):
        print self.backup_id
        self._delete_backup(self.backup_id)
        assert_equal(202, instance_info.dbaas.last_http_code)
        def backup_is_gone():
            result = None
            try:
                result = instance_info.dbaas.backups.get(self.backup_id)
            except exceptions.NotFound:
                assert_equal(result.status, "404",
                             "Backup Resource not found)")
            finally:
                #print dir(result)
                if result is None:
                    return True
                else:
                    return False
        poll_until(backup_is_gone)


@test(depends_on_classes=[WaitForGuestInstallationToFinish],
      groups=[GROUP_NEGATIVE])
class TestBackupNegative(object):

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




    # @test
    # def test_backup_create_instance_not_found(self):
    #     """test create backup with unknown instance"""
    #     assert_raises(exceptions.NotFound, instance_info.dbaas.backups.create,
    #                   BACKUP_NAME, 'nonexistent_instance', BACKUP_DESC)

#
#     @test
#     def test_instance_action_right_after_backup_create(self):
#         """test any instance action while backup is running"""
#         assert_unprocessable(instance_info.dbaas.instances.resize_instance,
#                              instance_info.id, 1)
#
#     @test
#     def test_backup_create_another_backup_running(self):
#         """test create backup when another backup is running"""
#         assert_unprocessable(instance_info.dbaas.backups.create,
#                              'backup_test2', instance_info.id,
#                              'test description2')
#
#     @test
#     def test_backup_delete_still_running(self):
#         """test delete backup when it is running"""
#         result = instance_info.dbaas.backups.list()
#         backup = result[0]
#         assert_unprocessable(instance_info.dbaas.backups.delete, backup.id)
#
#

#
#     @test
#     @time_out(60 * 30)
#     def test_backup_created(self):
#         # This version just checks the REST API status.
#         def result_is_active():
#             backup = instance_info.dbaas.backups.get(backup_info.id)
#             if backup.status == "COMPLETED":
#                 return True
#             else:
#                 assert_not_equal("FAILED", backup.status)
#                 return False
#
#         poll_until(result_is_active)
#
#

#     @test
#     def test_backup_get(self):
#         """test get backup"""
#         backup = instance_info.dbaas.backups.get(backup_info.id)
#         assert_equal(backup_info.id, backup.id)
#         assert_equal(backup_info.name, backup.name)
#         assert_equal(backup_info.description, backup.description)
#         assert_equal(instance_info.id, backup.instance_id)
#         assert_equal('COMPLETED', backup.status)
#
#
#
# @test(depends_on_classes=[RestoreUsingBackup],
#       runs_after=[RestoreUsingBackup],
#       groups=[GROUP])
# class WaitForRestoreToFinish(object):
#     """
#         Wait until the instance is finished restoring.
#     """
#
#     @test
#     @time_out(60 * 32)
#     def test_instance_restored(self):
#         if test_config.auth_strategy == "fake":
#             raise SkipTest("Skipping restore tests for fake mode.")
#
#         # This version just checks the REST API status.
#         def result_is_active():
#             instance = instance_info.dbaas.instances.get(restore_instance_id)
#             if instance.status == "ACTIVE":
#                 return True
#             else:
#                 # If its not ACTIVE, anything but BUILD must be
#                 # an error.
#                 assert_equal("BUILD", instance.status)
#                 if instance_info.volume is not None:
#                     assert_equal(instance.volume.get('used', None), None)
#                 return False
#
#         poll_until(result_is_active)
#
#
# @test(runs_after=[WaitForRestoreToFinish],
#       groups=[GROUP])
# class DeleteBackups(object):
#
#     @test
#     def test_backup_delete_not_found(self):
#         """test delete unknown backup"""
#         assert_raises(exceptions.NotFound, instance_info.dbaas.backups.delete,
#                       'nonexistent_backup')

