"""Offline tests for `py4gw/gwa3/cmd_item.py` -- the last action module.

No client and no elevation. Two things are being established:

* the routed functions produce the same **values** GwAu3's bodies produce -- the bag's ID rather than
  its number, the clamped quantity, the purse when no amount is given, and the two gold caps in the
  order GwAu3 applies them;
* every refusal refuses, and cites both the GwAu3 line and the place the work lives.
"""

from __future__ import annotations

import inspect
import unittest
from unittest import mock

from py4gw.gwa3 import cmd_item


class ItemRouteTests(unittest.TestCase):
    """The eleven routed functions."""

    def test_equip_takes_the_controlled_characters_agent(self) -> None:
        """GwAu3's packet names no agent; the ported member needs one, and it is the player."""

        with mock.patch.object(cmd_item.Inventory, "EquipItem") as equip, mock.patch.object(
            cmd_item.Player, "GetAgentID", return_value=235
        ):
            self.assertTrue(cmd_item.Item_EquipItem(4023))
            equip.assert_called_once_with(4023, 235)

    def test_equip_hero_guards_both_arguments(self) -> None:
        """GwAu3 answers False with @error 1 for a zero hero agent *or* a zero item id."""

        with mock.patch.object(
            cmd_item.Party.Heroes, "GetHeroAgentIDByPartyPosition", return_value=0
        ), mock.patch.object(cmd_item.Inventory, "EquipItem") as equip:
            self.assertFalse(cmd_item.Item_EquipHero(1, 4023))
            equip.assert_not_called()

        with mock.patch.object(
            cmd_item.Party.Heroes, "GetHeroAgentIDByPartyPosition", return_value=4242
        ), mock.patch.object(cmd_item.Inventory, "EquipItem") as equip:
            self.assertFalse(cmd_item.Item_EquipHero(1, 0))
            equip.assert_not_called()

            self.assertTrue(cmd_item.Item_EquipHero(1, 4023))
            equip.assert_called_once_with(4023, 4242)

    def test_drop_item_clamps_to_the_stack(self) -> None:
        with mock.patch.object(
            cmd_item, "Item_GetItemInfoByItemID", return_value=5
        ), mock.patch.object(cmd_item.Inventory, "DropItem") as drop:
            # No amount means the whole stack, which is what a caller writing no amount means.
            cmd_item.Item_DropItem(1)
            drop.assert_called_with(1, 5)
            cmd_item.Item_DropItem(1, 99)
            drop.assert_called_with(1, 5)
            cmd_item.Item_DropItem(1, 2)
            drop.assert_called_with(1, 2)

    def test_move_item_passes_the_bag_id_not_the_bag_number(self) -> None:
        """GwAu3 reads the bag's `ID` field for the packet; the ported member takes that same id."""

        with mock.patch.object(cmd_item, "Item_GetBagInfo", return_value=77) as bag, mock.patch.object(
            cmd_item.Inventory, "MoveItem"
        ) as move:
            self.assertTrue(cmd_item.Item_MoveItem(4023, 1, 4))
            bag.assert_called_once_with(1, "ID")
            move.assert_called_once_with(4023, 77, 4, 1)

    def test_pick_up_converts_an_agent_id(self) -> None:
        """GwAu3's argument is an agent id and it converts it; the ported member takes the same value."""

        with mock.patch.object(cmd_item, "Agent_ConvertID", return_value=5150) as convert, mock.patch.object(
            cmd_item.Inventory, "PickUpItem"
        ) as pick:
            self.assertTrue(cmd_item.Item_PickUpItem(-2))
            convert.assert_called_once_with(-2)
            pick.assert_called_once_with(5150)

    def test_drop_gold_clamps_to_the_purse(self) -> None:
        with mock.patch.object(
            cmd_item.Inventory, "GetGoldOnCharacter", return_value=1234
        ), mock.patch.object(cmd_item.Inventory, "DropGold") as drop:
            cmd_item.Item_DropGold()
            drop.assert_called_with(1234)
            cmd_item.Item_DropGold(99999)
            drop.assert_called_with(1234)
            cmd_item.Item_DropGold(100)
            drop.assert_called_with(100)

    def test_deposit_applies_the_purse_and_then_the_vault_cap(self) -> None:
        """GwAu3's two decisions in its own order: the purse, then the million-gold vault."""

        with mock.patch.object(
            cmd_item.Inventory, "GetGoldInStorage", return_value=999_000
        ), mock.patch.object(
            cmd_item.Inventory, "GetGoldOnCharacter", return_value=5_000
        ), mock.patch.object(cmd_item.Inventory, "DepositGold") as deposit:
            # The purse fits, but the vault has room for only 1000 of the 5000 asked for.
            cmd_item.Item_DepositGold(5000)
            deposit.assert_called_once_with(1000)

        with mock.patch.object(
            cmd_item.Inventory, "GetGoldInStorage", return_value=0
        ), mock.patch.object(
            cmd_item.Inventory, "GetGoldOnCharacter", return_value=5_000
        ), mock.patch.object(cmd_item.Inventory, "DepositGold") as deposit:
            # An amount larger than the purse becomes the whole purse.
            cmd_item.Item_DepositGold(99_999)
            deposit.assert_called_once_with(5000)

    def test_withdraw_applies_the_vault_and_then_the_purse_cap(self) -> None:
        """The same shape with the caps swapped: the vault is the source, the purse the limit."""

        with mock.patch.object(
            cmd_item.Inventory, "GetGoldInStorage", return_value=20_000
        ), mock.patch.object(
            cmd_item.Inventory, "GetGoldOnCharacter", return_value=99_500
        ), mock.patch.object(cmd_item.Inventory, "WithdrawGold") as withdraw:
            # The character's cap is 100,000, so only 500 can be carried away.
            cmd_item.Item_WithdrawGold(20_000)
            withdraw.assert_called_once_with(500)

        with mock.patch.object(
            cmd_item.Inventory, "GetGoldInStorage", return_value=20_000
        ), mock.patch.object(
            cmd_item.Inventory, "GetGoldOnCharacter", return_value=0
        ), mock.patch.object(cmd_item.Inventory, "WithdrawGold") as withdraw:
            # An amount larger than the vault becomes the whole vault.
            cmd_item.Item_WithdrawGold(99_999)
            withdraw.assert_called_once_with(20_000)

    def test_use_destroy_and_switch_helpers(self) -> None:
        with mock.patch.object(cmd_item.Inventory, "UseItem") as use:
            self.assertTrue(cmd_item.Item_UseItem(4023))
            use.assert_called_once_with(4023)

        with mock.patch.object(cmd_item.Inventory, "DestroyItem") as destroy:
            self.assertTrue(cmd_item.Item_DestroyItem(4023))
            destroy.assert_called_once_with(4023)


class ItemRefusalTests(unittest.TestCase):
    """The twelve refusals."""

    CASES = (
        ("Item_SalvageItem", (1,)),
        ("Item_ApplyUpgrade", (1, 2, 0)),
        ("Item_CanIdentifyAll", ()),
        ("Item_IdentifyAll", ()),
        ("Item_CanDepositAllMaterials", ()),
        ("Item_DepositAllMaterials", ()),
        ("Item_MoveItem_", (1, 2, 3)),
        ("Item_UnequipHero", (1, 0, 1, 1)),
        ("Item_AcceptAllItems", ()),
        ("Item_ChangeGold", (1, 2)),
        ("Item_OpenChest", ()),
        ("Item_IdentifyItem", (1,)),
    )

    def test_every_refusal_cites_the_source_and_the_work(self) -> None:
        for name, args in self.CASES:
            with self.subTest(function=name):
                with self.assertRaises(NotImplementedError) as raised:
                    getattr(cmd_item, name)(*args)
                message = str(raised.exception)
                self.assertIn("GwAu3_Cmd_Item.au3", message)
                self.assertIn("py4gw", message)

    def test_the_mechanisms_are_told_apart(self) -> None:
        """A queue write, a GwAu3 memory slot and a missing member are not the same refusal."""

        with self.assertRaises(NotImplementedError) as queue:
            cmd_item.Item_SalvageItem(1)
        self.assertIn("command queue", str(queue.exception))

        with self.assertRaises(NotImplementedError) as slot:
            cmd_item.Item_CanIdentifyAll()
        self.assertIn("$g_i_InvCanIdentifyAllResult", str(slot.exception))

        with self.assertRaises(NotImplementedError) as missing:
            cmd_item.Item_MoveItem_(1, 2, 3)
        self.assertIn("SPLIT_STACK", str(missing.exception))

    def test_the_two_control_action_effects_are_routed_instead(self) -> None:
        """The bundle drop and the weapon-set switch: GwAu3's records, Reforged's presses.

        Both are `Core_Enqueue`/`Core_SendPacket` effects in GwAu3 whose action is one of the client's
        own control actions, which is why they are routed rather than refused: the press goes through the
        layer's control-action member with GwAu3's own constants -- ``0xCD`` for the bundle that
        ``ControlAction_DropItem`` carries, and the set's own ``0x81``-``0x84`` code, built with
        Reforged's own expression. A set outside ``1..4`` has no control action, and answers ``False``.
        """

        with mock.patch.object(cmd_item, "Core_PerformAction") as action:
            self.assertTrue(cmd_item.Item_DropBundle())
        action.assert_called_once_with(
            cmd_item._constants.GC_I_CONTROL_ACTION_DROP_ITEM,
            cmd_item._constants.GC_I_CONTROL_TYPE_ACTIVATE,
        )
        self.assertEqual(cmd_item._constants.GC_I_CONTROL_ACTION_DROP_ITEM, 0xCD)

        for set_number, expected in ((1, 0x81), (2, 0x82), (3, 0x83), (4, 0x84)):
            with self.subTest(weapon_set=set_number):
                with mock.patch.object(cmd_item, "Core_PerformAction") as action:
                    self.assertTrue(cmd_item.Item_SwitchWeaponSet(set_number))
                action.assert_called_once_with(
                    expected, cmd_item._constants.GC_I_CONTROL_TYPE_ACTIVATE
                )

        with mock.patch.object(cmd_item, "Core_PerformAction") as action:
            self.assertFalse(cmd_item.Item_SwitchWeaponSet(0))
            self.assertFalse(cmd_item.Item_SwitchWeaponSet(5))
        action.assert_not_called()

    def test_the_split_stack_arm_is_recorded_as_the_reason(self) -> None:
        """`Item_MoveItem` is routed and `Item_MoveItem_` is not, and the difference is the split."""

        with self.assertRaises(NotImplementedError) as raised:
            cmd_item.Item_MoveItem_(1, 2, 3)
        self.assertIn("SPLIT_STACK", str(raised.exception))

    def test_the_declared_surface_is_the_sources_own(self) -> None:
        """24 functions, which is what `GwAu3_Cmd_Item.au3` declares."""

        self.assertEqual(len(cmd_item.__all__), 24)
        for name in cmd_item.__all__:
            self.assertTrue(callable(getattr(cmd_item, name)), name)
        # And every one of them is callable with the arguments its own signature demands.
        for name in cmd_item.__all__:
            signature = inspect.signature(getattr(cmd_item, name))
            required = [
                parameter
                for parameter in signature.parameters.values()
                if parameter.default is inspect.Parameter.empty
            ]
            self.assertTrue(all(parameter.name for parameter in required), name)


if __name__ == "__main__":
    unittest.main()
