#  Drakkar-Software OctoBot
#  Copyright (c) Drakkar-Software, All rights reserved.
#
#  This library is free software; you can redistribute it and/or
#  modify it under the terms of the GNU Lesser General Public
#  License as published by the Free Software Foundation; either
#  version 3.0 of the License, or (at your option) any later version.
#
#  This library is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
#  Lesser General Public License for more details.
#
#  You should have received a copy of the GNU Lesser General Public
#  License along with this library.
import pytest
import os
import contextlib
import json
import asyncio

import octobot_commons.databases as databases
import octobot_commons.symbols as commons_symbols
import octobot_backtesting.enums as enums
import octobot_backtesting.errors as errors
import octobot_trading.enums as trading_enums
import tests.test_utils.config as test_utils_config
import tentacles.Backtesting.collectors.exchanges as collector_exchanges
import tentacles.Trading.Exchange as tentacles_exchanges

# All test coroutines will be treated as marked.
pytestmark = pytest.mark.asyncio

BINANCE = "binance"
BINANCE_MAX_CANDLES_COUNT = 500


@contextlib.asynccontextmanager
async def data_collector(exchange_name, tentacles_setup_config, symbols, time_frames, use_all_available_timeframes,
                         start_timestamp=None, end_timestamp=None):
    collector_instance = collector_exchanges.ExchangeHistoryDataCollector(
        {}, exchange_name, trading_enums.ExchangeTypes.SPOT, tentacles_setup_config,
        [commons_symbols.parse_symbol(symbol) for symbol in symbols], time_frames,
        use_all_available_timeframes=use_all_available_timeframes,
        start_timestamp=start_timestamp,
        end_timestamp=end_timestamp
    )
    try:
        await collector_instance.initialize()
        yield collector_instance
    finally:
        if collector_instance.file_path and os.path.isfile(collector_instance.file_path):
            os.remove(collector_instance.file_path)
        if collector_instance.temp_file_path and os.path.isfile(collector_instance.temp_file_path):
            os.remove(collector_instance.temp_file_path)


@contextlib.asynccontextmanager
async def collector_database(collector):
    database = databases.SQLiteDatabase(collector.file_path)
    try:
        await database.initialize()
        yield database
    finally:
        await database.stop()


async def test_collect_valid_data():
    tentacles_setup_config = test_utils_config.load_test_tentacles_config()
    symbols = ["ETH/BTC"]
    async with data_collector(BINANCE, tentacles_setup_config, symbols, None, True) as collector:
        assert collector.time_frames == []
        assert collector.symbols == [commons_symbols.parse_symbol(symbol) for symbol in symbols]
        assert collector.exchange_name == BINANCE
        assert collector.tentacles_setup_config == tentacles_setup_config
        await collector.start()
        assert collector.time_frames != []
        assert collector.exchange_manager is None
        assert isinstance(collector.exchange, tentacles_exchanges.Binance)
        assert collector.file_path is not None
        assert collector.temp_file_path is not None
        assert not os.path.isfile(collector.temp_file_path)
        assert os.path.isfile(collector.file_path)
        async with collector_database(collector) as database:
            ohlcv = await database.select(enums.ExchangeDataTables.OHLCV)
            # use > to take into account new possible candles since collect max time is not specified
            assert len(ohlcv) > 6000
            h_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")
            assert len(h_ohlcv) == BINANCE_MAX_CANDLES_COUNT
            eth_btc_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, symbol="ETH/BTC")
            assert len(eth_btc_ohlcv) == len(ohlcv)


async def test_collect_invalid_data():
    tentacles_setup_config = test_utils_config.load_test_tentacles_config()
    symbols = ["___ETH/BTC"]
    async with data_collector(BINANCE, tentacles_setup_config, symbols, None, True) as collector:
        with pytest.raises(errors.DataCollectorError):
            await collector.start()
        assert collector.time_frames != []
        assert collector.exchange_manager is None
        assert collector.exchange is not None
        assert collector.file_path is not None
        assert collector.temp_file_path is not None
        assert not os.path.isfile(collector.temp_file_path)


async def test_collect_valid_date_range():
    tentacles_setup_config = test_utils_config.load_test_tentacles_config()
    symbols = ["ETH/BTC"]
    async with data_collector(BINANCE, tentacles_setup_config, symbols, None, True, 1549065660000, 1549670520000) as collector:
        assert collector.start_timestamp is not None
        assert collector.end_timestamp is not None
        await collector.start()
        assert collector.time_frames != []
        assert collector.exchange_manager is None
        assert isinstance(collector.exchange, tentacles_exchanges.Binance)
        assert collector.file_path is not None
        assert collector.temp_file_path is not None
        assert os.path.isfile(collector.file_path)
        assert not os.path.isfile(collector.temp_file_path)
        async with collector_database(collector) as database:
            ohlcv = await database.select(enums.ExchangeDataTables.OHLCV)
            assert len(ohlcv) == 16833
            h_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, time_frame="1h")
            assert len(h_ohlcv) == 168
            eth_btc_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, symbol="ETH/BTC")
            assert len(eth_btc_ohlcv) == len(ohlcv)
            min_timestamp = (await database.select_min(enums.ExchangeDataTables.OHLCV, ["timestamp"],
                                                       time_frame="1m"))[0][0]*1000
            assert min_timestamp <= 1549065720000
            max_timestamp = (await database.select_max(enums.ExchangeDataTables.OHLCV, ["timestamp"]))[0][0]*1000
            assert max_timestamp <= 1549843200000


async def test_collect_invalid_date_range():
    tentacles_setup_config = test_utils_config.load_test_tentacles_config()
    symbols = ["ETH/BTC"]
    async with data_collector(BINANCE, tentacles_setup_config, symbols, None, True, 1609459200, 1577836800) \
            as collector:
        assert collector.start_timestamp is not None
        assert collector.end_timestamp is not None
        with pytest.raises(errors.DataCollectorError):
            await collector.start()
        assert collector.time_frames != []
        assert collector.exchange_manager is None
        assert isinstance(collector.exchange, tentacles_exchanges.Binance)
        assert collector.file_path is not None
        assert collector.temp_file_path is not None
        assert not os.path.isfile(collector.file_path)
        assert not os.path.isfile(collector.temp_file_path)


async def test_collect_multi_pair():
    tentacles_setup_config = test_utils_config.load_test_tentacles_config()
    symbols = ["ETH/BTC", "BTC/USDT", "1INCH/BTC"]
    async with data_collector(BINANCE, tentacles_setup_config, symbols, None, True) as collector:
        assert collector.time_frames == []
        assert collector.symbols == [commons_symbols.parse_symbol(symbol) for symbol in symbols]
        assert collector.exchange_name == BINANCE
        assert collector.tentacles_setup_config == tentacles_setup_config
        await collector.start()
        assert collector.time_frames != []
        assert collector.exchange_manager is None
        assert isinstance(collector.exchange, tentacles_exchanges.Binance)
        assert collector.file_path is not None
        assert collector.temp_file_path is not None
        assert not os.path.isfile(collector.temp_file_path)
        assert os.path.isfile(collector.file_path)
        async with collector_database(collector) as database:
            ohlcv = await database.select(enums.ExchangeDataTables.OHLCV)
            # use > to take into account new possible candles since collect max time is not specified
            assert len(ohlcv) > 19316
            h_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, time_frame="4h")
            assert len(h_ohlcv) == len(symbols) * BINANCE_MAX_CANDLES_COUNT
            symbols_description = json.loads((await database.select(enums.DataTables.DESCRIPTION))[0][3])
            assert all(symbol in symbols_description for symbol in symbols)
            eth_btc_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, symbol="ETH/BTC")
            assert len(eth_btc_ohlcv) > 6760
            inch_btc_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, symbol="1INCH/BTC")
            assert len(inch_btc_ohlcv) > 5803
            btc_usdt_ohlcv = await database.select(enums.ExchangeDataTables.OHLCV, symbol="BTC/USDT")
            assert len(btc_usdt_ohlcv) > 6743


async def test_stop_collect():
    tentacles_setup_config = test_utils_config.load_test_tentacles_config()
    symbols = ["AAVE/USDT"]
    async with data_collector(BINANCE, tentacles_setup_config, symbols, None, True, 1549065660000,
                              1632090006000) as collector:
        async def stop_soon():
            await asyncio.sleep(5)
            await collector.stop(should_stop_database=False)

        await asyncio.gather(collector.start(), stop_soon())
        assert collector.time_frames != []
        assert collector.symbols == [commons_symbols.parse_symbol(symbol) for symbol in symbols]
        assert collector.exchange_name == BINANCE
        assert collector.tentacles_setup_config == tentacles_setup_config
        assert collector.finished
        assert collector.exchange_manager is None
        assert not os.path.isfile(collector.temp_file_path)
        assert not os.path.isfile(collector.file_path)
