import brownie
from brownie import Contract
from brownie import config

# test passes as of 21-06-26
def test_triggers(
    gov, token, vault, dudesahn, strategist, whale, strategy, chain, strategist_ms,
):
    ## deposit to the vault after approving
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})
    newWhale = token.balanceOf(whale)
    starting_assets = vault.totalAssets()
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)

    # simulate a day of earnings
    chain.sleep(86400)
    chain.mine(1)

    # harvest should trigger false
    tx = strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be False.", tx)
    assert tx == False

    # simulate eight days of earnings
    chain.sleep(86400 * 8)
    chain.mine(1)

    # harvest should trigger true
    tx = strategy.harvestTrigger(0, {"from": gov})
    print("\nShould we harvest? Should be true.", tx)
    chain.sleep(1)
    strategy.harvest({"from": gov})
    chain.sleep(1)
    assert tx == True

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money
    vault.withdraw({"from": whale})
    assert token.balanceOf(whale) > startingWhale
