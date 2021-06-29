import brownie
from brownie import Wei, accounts, Contract, config

# test passes as of 21-06-26
def test_cloning(
    gov,
    token,
    vault,
    dudesahn,
    strategist,
    whale,
    strategy,
    keeper,
    rewards,
    chain,
    strategist_ms,
    staking,
    StrategyUniverseStaking,
    rewardscontract,
):

    # Shouldn't be able to call initialize again
    with brownie.reverts():
        strategy.initialize(
            vault, strategist, rewards, keeper, rewardscontract, {"from": gov},
        )

    ## clone our strategy
    tx = strategy.clone(vault, strategist, rewards, keeper, rewardscontract)
    newStrategy = StrategyUniverseStaking.at(tx.return_value)

    # Shouldn't be able to call initialize again
    with brownie.reverts():
        newStrategy.initialize(
            vault, strategist, rewards, keeper, rewardscontract, {"from": gov},
        )

    vault.revokeStrategy(strategy, {"from": gov})
    vault.addStrategy(newStrategy, 10_000, 0, 2 ** 256 - 1, 1_000, {"from": gov})
    assert vault.withdrawalQueue(1) == newStrategy
    assert vault.strategies(newStrategy)[2] == 10_000
    assert vault.withdrawalQueue(0) == strategy
    assert vault.strategies(strategy)[2] == 0

    ## deposit to the vault after approving; this is basically just our simple_harvest test
    before_pps = vault.pricePerShare()
    startingWhale = token.balanceOf(whale)
    token.approve(vault, 2 ** 256 - 1, {"from": whale})
    vault.deposit(1000e18, {"from": whale})

    # harvest, store asset amount
    newStrategy.harvest({"from": gov})
    old_assets_dai = vault.totalAssets()
    assert old_assets_dai > 0
    assert token.balanceOf(newStrategy) == 0
    assert newStrategy.estimatedTotalAssets() > 0
    assert staking.balanceOf(newStrategy, token) > 0
    print("\nStarting Assets: ", old_assets_dai / 1e18)
    print("\nAssets Staked: ", staking.balanceOf(newStrategy, token) / 1e18)

    # simulate 9 days of earnings
    chain.sleep(86400 * 9)
    chain.mine(1)

    # harvest after a day, store new asset amount
    newStrategy.harvest({"from": gov})
    new_assets_dai = vault.totalAssets()
    # we can't use strategyEstimated Assets because the profits are sent to the vault
    assert new_assets_dai >= old_assets_dai
    print("\nAssets after 2 days: ", new_assets_dai / 1e18)

    # Display estimated APR based on the two days before the pay out
    print(
        "\nEstimated SUSHI APR: ",
        "{:.2%}".format(
            ((new_assets_dai - old_assets_dai) * (365 / 9))
            / (newStrategy.estimatedTotalAssets())
        ),
    )

    # simulate a day of waiting for share price to bump back up
    chain.sleep(86400)
    chain.mine(1)

    # withdraw and confirm we made money
    vault.withdraw({"from": whale})
    assert token.balanceOf(whale) >= startingWhale
    assert vault.pricePerShare() > before_pps
