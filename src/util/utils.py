#!/usr/bin/env/ python3
# -*- coding: utf-8 -*-
# @Filename: utils
# @Date:   : 2017-11-27 17:27
# @Author  : YuJun
# @Email   : yujun_mail@163.com

from src.util import cons as ct
import os
import pandas as pd
import numpy as np
from pandas import Series
from pandas import DataFrame
import tushare as ts
import datetime
import shelve
from src.util.Cache import Cache


class Utils(object):

    _DataCache = Cache(500)    # 数据缓存

    @classmethod
    def calc_interval_ret(cls, secu_code, start=None, end=None, ndays=None):
        """
        计算证券区间收益率
        计算区间分三种方式指定：
        （1）指定开始、结束日期，即start和end不为空，此时忽略参数ndays
        （2）指定开始日期、天数，即start和ndays不为空，而end为空
        （3）指定结束日期、天数，即end和ndays不为空，而start为空
        --------
        :param secu_code: string
            证券代码，e.g. 600000
        :param start: string or datetime-like
            开始日期，格式：YYYY-MM-DD
        :param end: string or datetime-like
            结束日期，格式：YYYY-MM-DD
        :param ndays: int
            交易日天数
        :return:
        --------
            float，证券的区间收益率
        """
        symbol = _code_to_symbol(secu_code)
        file_path = '%s.csv' % (os.path.join(ct.DB_PATH, ct.MKT_DAILY_FQ, symbol))
        headers = ['code', 'date', 'open', 'high', 'low', 'close', 'vol', 'amount', 'turnover1', 'turnover2', 'factor']
        df_mkt = pd.read_csv(file_path, names=headers, header=0)
        # 如果start或end是datetime.datetime/datetime.date类型，将其转化为字符串
        if isinstance(start, datetime.datetime) or isinstance(start, datetime.date):
            start = start.strftime('%Y-%m-%d')
        if isinstance(end, datetime.datetime) or isinstance(end, datetime.date):
            end = end.strftime('%Y-%m-%d')
        if start is not None and end is not None:
            # 取得开始日期前一交易日和结束日期之间的索引值列表，根据这个索引值列表取得复权行情切片，计算区间收益率
            inds = list(df_mkt[(df_mkt.date >= start) & (df_mkt.date <= end)].index.values)
            if len(inds) > 0:
                if inds[0] > 0:
                    inds.insert(0, inds[0]-1)
                    df_mkt = df_mkt.ix[inds]
                else:
                    # 如果开始日期小于等于该证券上市日期，那么把第一天的收盘价设置为开盘价
                    df_mkt.iloc[0, 5] = df_mkt.iat[0, 3]
                interval_ret = df_mkt.iloc[-1, 5]/df_mkt.iloc[0, 5] - 1.0
            else:
                # 如果在指定的开始、结束日期间该证券没有行情数据，返回None
                interval_ret = None
        elif start is not None and ndays is not None:
            try:
                start_ind = df_mkt[df_mkt.date >= start].iloc[0].name
            except IndexError:
                start_ind = -1
            if start_ind < 0:
                interval_ret = None
            else:
                if start_ind <= df_mkt.iloc[0].name:
                    start_close = df_mkt.iloc[0].open
                else:
                    start_close = df_mkt.loc[start_ind-1, 'close']
                end_ind = start_ind + ndays - 1
                if end_ind > df_mkt.iloc[-1].name:
                    end_ind = df_mkt.iloc[-1].name
                end_close = df_mkt.loc[end_ind, 'close']
                interval_ret = end_close / start_close - 1.0
        elif end is not None and ndays is not None:
            try:
                end_ind = df_mkt[df_mkt.date <= end].iloc[-1].name
            except IndexError:
                end_ind = -1
            if end_ind < 0:
                interval_ret = None
            else:
                end_close = df_mkt.loc[end_ind, 'close']
                start_ind = end_ind - ndays
                if start_ind < df_mkt.iloc[0].name:
                    start_close = df_mkt.iloc[0].open
                else:
                    start_close = df_mkt.loc[start_ind, 'close']
                interval_ret = end_close / start_close - 1.0
        else:
            interval_ret = None
        return interval_ret

    # 交易日序列静态变量，Series
    utils_trading_days = Series()

    @classmethod
    def get_trading_days(cls, start=None, end=None, ndays=None, ascending=True):
        """
        取得交易日列表，分三种方式取得
        （1）指定开始、结束日期，即start和end不为None，此时忽略参数ndays
        （2）指定开始日期和天数，即start和ndays不为None，而end为None
        （3）指定结束日期和天数，即end和ndays为None，而start为None
        --------
        :param start: datetime-like or str
            开始日期，格式：YYYY-MM-DD
        :param end: datetime-like or str
            结束日期，格式：YYYY-MM-DD
        :param ndays: int
            交易日天数
        :param ascending: bool，默认True
            是否升序排列
        :return:
        --------
            Series of pandas.Timestamp，交易日列表，默认按交易日升序排列
        """
        if len(Utils.utils_trading_days) == 0:
            ts_conn = ts.get_apis()
            df_SZZS = ts.bar(code='000001', conn=ts_conn, asset='INDEX')
            ts.close_apis(ts_conn)
            Utils.utils_trading_days = Series(df_SZZS.index).sort_values()
        if start is not None and end is not None:
            trading_days = Utils.utils_trading_days[(Utils.utils_trading_days >= start) & (Utils.utils_trading_days <= end)]
        elif start is not None and ndays is not None:
            trading_days = Utils.utils_trading_days[Utils.utils_trading_days >= start].iloc[:ndays]
        elif end is not None and ndays is not None:
            trading_days = Utils.utils_trading_days[Utils.utils_trading_days <= end].iloc[-ndays:]
        elif start is not None:
            trading_days = Utils.utils_trading_days[Utils.utils_trading_days >= start]
        elif end is not None:
            trading_days = Utils.utils_trading_days[Utils.utils_trading_days <= end]
        elif ndays is not None:
            trading_days = Utils.utils_trading_days[-ndays:]
        else:
            trading_days = Utils.utils_trading_days
        trading_days = trading_days.reset_index(drop=True)
        if not ascending:
            trading_days = trading_days.sort_values(ascending=False)
        return trading_days

    @classmethod
    def is_month_end(cls, trading_day):
        """
        是否时月末的交易日
        :param trading_day: datetime-like, str
        :return: bool
        """
        trading_day = Utils.to_date(trading_day)
        trading_days = Utils.get_trading_days(start=trading_day, ndays=2)
        if trading_day != trading_days[0]:
            return False
        else:
            if trading_day.month == trading_days[1].month:
                return False
            else:
                return True


    @classmethod
    def get_secu_daily_mkt(cls, secu_code, start, end=None, fq=False, range_lookup=False):
        """
        读取证券的日行情数据
        Parameters
        --------
        :param secu_code: str
            证券代码，e.g. 600000
        :param start: datetime-like, str
            开始日期，格式：YYYY-MM-DD
        :param end: datetime-like, str，默认None
            结束日期，格式：YYYY-MM-DD；当end=None时，只取start一天的行情数据
        :param fq: bool，默认False
            是否读取复权行情数据
        :param range_lookup: bool，默认False
            是否模糊匹配，False=精确匹配，True=模糊匹配，该参数仅对end=None时适用，
            当range_lookup=False，返回trading_day=start的行情数据，没有行情数据返回空数据。
            当range_lookup=True，如果start没有行情数据时，返回start之前最近一个交易日行情数据.
        :return:
        --------
            1.如果end=None，返回Series
            2.如果end!=None，返回DataFrame
            code    证券代码
            date    日期
            open    开盘价
            high    最高价
            low     最低价
            close   收盘价
            vol     成交量
            amount  成交金额
            turnover1   流通盘换手率
            turnover2   全流通换手率
            factor  复权系数
        """
        symbol = _code_to_symbol(secu_code)
        if fq:
            file_path = '%s.csv' % os.path.join(ct.DB_PATH, ct.MKT_DAILY_FQ, symbol)
            df_mkt = pd.read_csv(file_path, names=ct.MKT_DAILY_FQ_HEADER, header=0)
        else:
            file_path = '%s.csv' % os.path.join(ct.DB_PATH, ct.MKT_DAILY_NOFQ, symbol)
            df_mkt = pd.read_csv(file_path, names=ct.MKT_DAILY_NOFQ_HEADER, header=0)
        start = cls.datetimelike_to_str(start, dash=True)
        if end is not None:
            end = cls.datetimelike_to_str(end, dash=True)
            return df_mkt[(df_mkt.date >= start) & (df_mkt.date <= end)]
        else:
            if range_lookup:
                mkt_data = df_mkt[df_mkt.date <= start].iloc[-1]
            else:
                mkt_data = df_mkt[df_mkt.date == start]
                if mkt_data.shape[0] == 0:
                    mkt_data = Series()
                else:
                    mkt_data = mkt_data.iloc[0]
            return mkt_data

    @classmethod
    def get_min_mkt(cls, code, trade_date, index=False, fq=False):
        """
        获取证券（个股或指数）指定日期的分钟行情数据
        Parameters:
        --------
        :param code: string
            证券代码，如600000,SH600000,SZ000002
        :param trade_date: datetime-like, str
            交易日，当类型为str时格式为YYYY-MM-DD
        :param index: bool,默认False
        :param fq: bool,默认False
            是否复权
        :return:
            证券分钟行情数据，DataFrame
        --------
        DataFrame
            0: code，个股代码，如SH600000
            1: time，时间，格式YYYY-MM-DD hh:mm:ss
            2: open，开盘价
            3: high，最高价
            4: low，最低价
            5: close，收盘价
            6: volume，成交量(手)
            7: amount，成交金额(元)
            8: factor，复权系数
            如果没有行情数据返回None
        """
        symbol = cls.code_to_symbol(code, index)
        str_date = cls.datetimelike_to_str(trade_date)
        if fq:
            mkt_file_path = os.path.join(ct.DB_PATH, ct.MKT_MIN_FQ, str_date, '%s.csv' % symbol)
        else:
            mkt_file_path = os.path.join(ct.DB_PATH, ct.MKT_MIN_NOFQ, str_date, '%s.csv' % symbol)
        key = '%s_1min_mkt_%s' % (symbol, cls.to_date(trade_date).strftime('%Y%m%d'))
        df_mkt_min = cls._DataCache.get(key)
        if df_mkt_min is None and os.path.isfile(mkt_file_path):
            df_mkt_min = pd.read_csv(mkt_file_path, names=ct.MKT_MIN_FQ_HEADER, skiprows=[0])
            cls._DataCache.set(key, df_mkt_min)
        # else:
        #     df_mkt_min = None
        return df_mkt_min

    @classmethod
    def factor_loading_persistent(cls, db_file, str_key, dict_factor_loading):
        """
        持久化因子载荷
        Parameters
        --------
        :param db_file: str
            因子载荷数据文件，绝对路径
        :param str_key: str
            持久化因子载荷时用到的key，一般为日期，格式YYYYMMDD
        :param dict_factor_loading: dict
            因子载荷值
        :return:
        """
        persistence_type = ct.FACTOR_LOADING_PERSISTENCE_TYPE.split(',')
        for perst_type in persistence_type:
            if perst_type == 'shelve':
                db = shelve.open(db_file, flag='c', protocol=None, writeback=False)
                try:
                    db[str_key] = dict_factor_loading
                    db.sync()
                finally:
                    db.close()
            elif perst_type == 'csv':
                db_file += '_%s.csv' % str_key
                DataFrame(dict_factor_loading).to_csv(db_file, index=False)

    @classmethod
    def read_factor_loading(cls, db_file, str_key):
        """
        从因子载荷持久化文件中读取指定str_key的因子载荷值
        Parameters
        --------
        :param db_file: str
            因子载荷数据文件，绝对路径
        :param str_key: str
            键值，一般为日期，格式为YYYYMMDD
        :return: DataFrame，因子载荷
        --------
            DataFrame:
            0: ID, 证券代码，如SH600000，为索引
            1: factorvalue,因子载荷
        """
        using_type = ct.USING_PERSISTENCE_TYPE
        if using_type == 'shelve':
            db = shelve.open(db_file, flag='c', protocol=None, writeback=False)
            try:
                dict_factor_loading = db[str_key]
                df_factor_loading = DataFrame(dict_factor_loading).set_index('ID')
            except KeyError:
                df_factor_loading = DataFrame()
            finally:
                db.close()
        elif using_type == 'csv':
            db_file &= '_%s.csv' % str_key
            df_factor_loading = pd.read_csv(db_file, header=0, index_col=0)
        else:
            df_factor_loading = DataFrame()
        return df_factor_loading

    @classmethod
    def clean_extreme_value(cls, arr_data, method='MAD'):
        """
        对数据进行去极值处理
        :param arr_data: np.array
            需要进行去极值的原始数据，数组的每一列各自进行去极值操作
        :param method: 去极值算法
        :return: np.array
            去极值处理后的数据
        """
        raw_data = arr_data.copy()
        m = np.median(raw_data, axis=0)     # 原始数据的中位数
        mad = np.median(np.fabs(raw_data - m), axis=0)
        fupper = m + mad * ct.CLEAN_EXTREME_VALUE_MULTI_CONST
        flower = m - mad - ct.CLEAN_EXTREME_VALUE_MULTI_CONST
        for k in range(raw_data.shape[1]):
            if method == 'MAD':
                raw_data[:, k][raw_data[:, k] > fupper[k]] = fupper[k]
                raw_data[:, k][raw_data[:, k] < flower[k]] = flower[k]
        return raw_data

    @classmethod
    def normalize_data(cls, arr_data):
        """
        对数据进行标准化
        :param arr_data: np.array
            需要进行标准化处理的原始数据
        :return: np.array
            标准化处理后的数据
        """
        raw_data = arr_data.copy()
        u = np.mean(raw_data, axis=0)
        s = np.std(raw_data, axis=0)
        return (raw_data - u)/s

    @classmethod
    def datetimelike_to_str(cls, datetime_like, dash=True):
        if isinstance(datetime_like, datetime.datetime) or isinstance(datetime_like, datetime.date):
            if dash:
                return datetime_like.strftime('%Y-%m-%d')
            else:
                return datetime_like.strftime('%Y%m%d')
        else:
            if dash:
                return datetime_like
            else:
                return datetime_like.replace('-', '')

    @classmethod
    def to_date(cls, date_like):
        if isinstance(date_like, datetime.datetime) or isinstance(date_like, datetime.date):
            return date_like
        else:
            return datetime.datetime.strptime(date_like.replace('-', ''), '%Y%m%d')

    @classmethod
    def code_to_symbol(cls, code, index=False):
        if not index:
            return _code_to_symbol(code)
        else:
            return _code_to_index_symbol(code)

    @classmethod

    @classmethod
    # 转换为适用于tushare格式的代码
    def code_to_tssymbol(cls, code, index=False):
        if len(code) != 6:
            return code
        else:
            if not index:
                return '%s.SH' % code if code[:1] in ['5', '6', '9'] else '%s.SZ' % code
            else:
                return '%s.SZ' % code if code[:3] == '399' else '%s.SH' % code


def _code_to_symbol(code):
    """
    生成本系统的证券代码symbol
    :param code:原始代码，如600000
    :return:
    """
    if len(code) != 6:
        return code
    else:
        return 'SH%s' % code if code[:1] in ['5', '6', '9'] else 'SZ%s' % code


def _code_to_index_symbol(code):
    """
    生成本系统的指数代码symbol
    :param code: 原始代码，如000001（上证综指）
    :return:
    """
    if len(code) != 6:
        return code
    else:
        return 'SZ%s' % code if code[:3] == '399' else 'SH%s' % code


if __name__ == '__main__':
    # test calc_interval_ret
    ret = Utils.calc_interval_ret('600000', start=datetime.datetime.strptime('2016-01-01', '%Y-%m-%d'), end='2016-10-16')
    print('ret = %0.4f' % ret)
    # test get_trading_days
    # trading_days = Utils.get_trading_days(start=datetime.datetime.strptime('2017-01-01', '%Y-%m-%d'), end='2017-10-31', ndays=10)
    # print(len(trading_days))
    # trading_days = Utils.get_trading_days(start=pd.Timestamp('2017-01-01'), end='2017-10-31', ndays=10)
    # print(len(trading_days))
    # trading_days = Utils.get_trading_days(start='2016-10-01', end='2017-10-31', ndays=10)
    # print(len(trading_days))
    # trading_days = Utils.get_trading_days()
    # print(len(trading_days))
    # test datetimelike_to_str
    print(Utils.datetimelike_to_str('2017-12-07', dash=False))
    print(Utils.datetimelike_to_str('20171207'))
    print(Utils.datetimelike_to_str(datetime.date(2017, 12, 7), dash=False))
    # test get_secu_daily_mkt
    mkt = Utils.get_secu_daily_mkt('600827', '2015-03-05', range_lookup=False)
    print(mkt)
    print(mkt.shape)