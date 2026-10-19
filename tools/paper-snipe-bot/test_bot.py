import unittest

from bot import Launch, PaperBot, run_simulation


def launch(score: float = 0.9, symbol: str = "TEST") -> Launch:
    return Launch(
        symbol=symbol,
        narrative="AI",
        liquidity=score,
        holder_growth=score,
        buy_pressure=score,
        mention_growth=score,
        sentiment=score,
        drift=0,
    )


class PaperBotTests(unittest.TestCase):
    def test_combines_onchain_and_social_scores(self) -> None:
        candidate = launch(0.8)
        self.assertAlmostEqual(candidate.onchain_score, 0.8)
        self.assertAlmostEqual(candidate.social_score, 0.8)
        self.assertAlmostEqual(candidate.score, 0.8)

    def test_buy_and_take_profit_return_virtual_cash_and_adjust_threshold(self) -> None:
        bot = PaperBot(starting_balance=1_000, threshold=0.6)
        self.assertTrue(bot.consider(launch(), 2.0, 1))
        self.assertEqual(bot.cash, 900)

        closed = bot.update({"TEST": 2.5}, 2)

        self.assertEqual(len(closed), 1)
        self.assertEqual(closed[0].reason, "take profit")
        self.assertAlmostEqual(closed[0].pnl, 25)
        self.assertAlmostEqual(bot.cash, 1_025)
        self.assertAlmostEqual(bot.threshold, 0.59)

    def test_loss_makes_strategy_more_selective(self) -> None:
        bot = PaperBot(starting_balance=1_000, threshold=0.6)
        bot.consider(launch(), 1.0, 1)

        bot.update({"TEST": 0.8}, 2)

        self.assertAlmostEqual(bot.threshold, 0.62)

    def test_closes_all_open_positions_at_simulation_end(self) -> None:
        bot = PaperBot(starting_balance=1_000, threshold=0.6, max_positions=2)
        bot.consider(launch(symbol="ONE"), 1.0, 1)
        bot.consider(launch(symbol="TWO"), 1.0, 1)

        closed = bot.close_positions({"ONE": 1.1, "TWO": 0.9}, "simulation ended")

        self.assertEqual(len(closed), 2)
        self.assertFalse(bot.positions)
        self.assertAlmostEqual(bot.cash, 1_000)

    def test_simulation_is_repeatable_and_closes_every_position(self) -> None:
        first_bot, first_log = run_simulation(20, 17, 1_000)
        second_bot, second_log = run_simulation(20, 17, 1_000)

        self.assertEqual(first_log, second_log)
        self.assertEqual(first_bot.trades, second_bot.trades)
        self.assertFalse(first_bot.positions)
        self.assertGreaterEqual(first_bot.cash, 0)

    def test_rejects_invalid_parameters(self) -> None:
        with self.assertRaises(ValueError):
            PaperBot(starting_balance=0)
        with self.assertRaises(ValueError):
            run_simulation(0, 1, 1_000)


if __name__ == "__main__":
    unittest.main()
