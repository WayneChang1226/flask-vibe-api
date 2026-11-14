from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError, OperationalError

from extensions import db
from models import Account, Transfer
from utils import json_response

ALLOWED_ACCOUNT_KINDS = {"cash", "bank", "credit_card", "broker"}

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")
transfers_bp = Blueprint("transfers", __name__, url_prefix="/api/transfers")


# ==========================================
# 帳戶路由 Accounts Routes
# ==========================================

@accounts_bp.route("", methods=["GET"], strict_slashes=False)
def list_accounts():
    accounts = Account.query.order_by(Account.id.asc()).all()
    return json_response(200, "取得帳戶清單成功", [a.to_dict() for a in accounts])


@accounts_bp.route("", methods=["POST"], strict_slashes=False)
def create_account():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    name_val = body.get("name")
    if name_val is None or str(name_val).strip() == "":
        return json_response(400, "帳戶名稱為必填項目")
    name = str(name_val).strip()

    kind_val = body.get("kind")
    if kind_val is None or str(kind_val).strip() == "":
        return json_response(400, "帳戶種類為必填項目")
    kind = str(kind_val).strip()
    if kind not in ALLOWED_ACCOUNT_KINDS:
        return json_response(400, "帳戶種類不合法，只允許 cash、bank、credit_card、broker")

    # 檢查帳戶名稱是否重複
    existing = Account.query.filter_by(name=name).first()
    if existing:
        return json_response(400, "帳戶名稱已被使用，請使用其他名稱")

    currency_val = body.get("currency")
    if currency_val is None or str(currency_val).strip() == "":
        currency = "TWD"
    else:
        currency = str(currency_val).strip().upper()
        if len(currency) != 3 or not currency.isalpha():
            return json_response(400, "幣別代碼必須為 3 碼英文字母")

    opening_balance_val = body.get("opening_balance")
    if opening_balance_val is None:
        opening_balance = Decimal("0")
    else:
        try:
            opening_balance = Decimal(str(opening_balance_val))
        except (InvalidOperation, TypeError, ValueError):
            return json_response(400, "期初餘額格式不正確")

    statement_day = body.get("statement_day")
    if statement_day is not None:
        try:
            statement_day = int(statement_day)
            if not (1 <= statement_day <= 31):
                return json_response(400, "結帳日必須介於 1 到 31 之間")
        except (TypeError, ValueError):
            return json_response(400, "結帳日必須為整數")

    payment_day = body.get("payment_day")
    if payment_day is not None:
        try:
            payment_day = int(payment_day)
            if not (1 <= payment_day <= 31):
                return json_response(400, "繳款日必須介於 1 到 31 之間")
        except (TypeError, ValueError):
            return json_response(400, "繳款日必須為整數")

    try:
        account = Account(
            name=name,
            kind=kind,
            currency=currency,
            opening_balance=opening_balance,
            statement_day=statement_day,
            payment_day=payment_day,
        )
        db.session.add(account)
        db.session.commit()
        return json_response(201, "帳戶建立成功", account.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


@accounts_bp.route("/<int:account_id>", methods=["GET"], strict_slashes=False)
def get_account(account_id: int):
    account = db.session.get(Account, account_id)
    if not account:
        return json_response(404, "找不到指定的帳戶")
    return json_response(200, "取得帳戶成功", account.to_dict())


@accounts_bp.route("/<int:account_id>", methods=["PATCH"], strict_slashes=False)
def update_account(account_id: int):
    account = db.session.get(Account, account_id)
    if not account:
        return json_response(404, "找不到指定的帳戶")

    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    if "name" in body:
        name_val = body.get("name")
        if name_val is None or str(name_val).strip() == "":
            return json_response(400, "帳戶名稱不能為空")
        new_name = str(name_val).strip()
        existing = Account.query.filter(Account.name == new_name, Account.id != account_id).first()
        if existing:
            return json_response(400, "帳戶名稱已被使用，請使用其他名稱")
        account.name = new_name

    if "statement_day" in body:
        s_day = body.get("statement_day")
        if s_day is None:
            account.statement_day = None
        else:
            try:
                s_day = int(s_day)
                if not (1 <= s_day <= 31):
                    return json_response(400, "結帳日必須介於 1 到 31 之間")
                account.statement_day = s_day
            except (TypeError, ValueError):
                return json_response(400, "結帳日必須為整數")

    if "payment_day" in body:
        p_day = body.get("payment_day")
        if p_day is None:
            account.payment_day = None
        else:
            try:
                p_day = int(p_day)
                if not (1 <= p_day <= 31):
                    return json_response(400, "繳款日必須介於 1 到 31 之間")
                account.payment_day = p_day
            except (TypeError, ValueError):
                return json_response(400, "繳款日必須為整數")

    # 改 updated_at
    account.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return json_response(200, "帳戶更新成功", account.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


@accounts_bp.route("/<int:account_id>/balance", methods=["GET"], strict_slashes=False)
def get_account_balance(account_id: int):
    account = db.session.get(Account, account_id)
    if not account:
        return json_response(404, "找不到指定的帳戶")

    opening = Decimal(str(account.opening_balance or 0))

    transfers_in = Transfer.query.filter_by(to_account_id=account.id).all()
    transfers_out = Transfer.query.filter_by(from_account_id=account.id).all()

    # 原幣別餘額：期初餘額 + 轉入 - 轉出
    orig_in = sum((Decimal(str(t.amount)) for t in transfers_in), Decimal("0"))
    orig_out = sum((Decimal(str(t.amount)) for t in transfers_out), Decimal("0"))
    original_balance = opening + orig_in - orig_out

    # 台幣餘額：轉入轉出金額先乘上該列的 fx_rate_to_twd
    twd_in = sum(
        (Decimal(str(t.amount)) * Decimal(str(t.fx_rate_to_twd)) for t in transfers_in),
        Decimal("0"),
    )
    twd_out = sum(
        (Decimal(str(t.amount)) * Decimal(str(t.fx_rate_to_twd)) for t in transfers_out),
        Decimal("0"),
    )
    twd_balance = opening + twd_in - twd_out

    data = {
        "account_id": account.id,
        "name": account.name,
        "currency": account.currency,
        "opening_balance": float(opening),
        "balance": float(original_balance),
        "original_currency_balance": float(original_balance),
        "twd_balance": float(twd_balance),
    }
    return json_response(200, "取得帳戶餘額成功", data)


# ==========================================
# 移轉路由 Transfers Routes
# ==========================================

@transfers_bp.route("", methods=["GET"], strict_slashes=False)
def list_transfers():
    transfers = Transfer.query.order_by(Transfer.transferred_on.desc(), Transfer.id.desc()).all()
    return json_response(200, "取得移轉清單成功", [t.to_dict() for t in transfers])


@transfers_bp.route("", methods=["POST"], strict_slashes=False)
def create_transfer():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON格式")

    transferred_on_val = body.get("transferred_on")
    if transferred_on_val is None or str(transferred_on_val).strip() == "":
        return json_response(400, "移轉日期為必填項目")
    try:
        transferred_on = datetime.strptime(str(transferred_on_val).strip(), "%Y-%m-%d").date()
    except ValueError:
        return json_response(400, "日期格式不正確，請使用 YYYY-MM-DD 格式")

    amount_val = body.get("amount")
    if amount_val is None:
        return json_response(400, "移轉金額為必填項目")
    try:
        amount = Decimal(str(amount_val))
        if amount <= 0:
            return json_response(400, "金額必須大於 0")
    except (InvalidOperation, TypeError, ValueError):
        return json_response(400, "金額格式不正確，必須為正數")

    currency_val = body.get("currency")
    if currency_val is None or str(currency_val).strip() == "":
        return json_response(400, "幣別為必填項目")
    currency = str(currency_val).strip().upper()
    if len(currency) != 3 or not currency.isalpha():
        return json_response(400, "幣別代碼必須為 3 碼英文字母")

    fx_rate_val = body.get("fx_rate_to_twd")
    if fx_rate_val is None:
        return json_response(400, "匯率為必填項目")
    try:
        fx_rate_to_twd = Decimal(str(fx_rate_val))
        if fx_rate_to_twd <= 0:
            return json_response(400, "匯率必須大於 0")
    except (InvalidOperation, TypeError, ValueError):
        return json_response(400, "匯率格式不正確，必須為正數")

    from_account_id_val = body.get("from_account_id")
    if from_account_id_val is None:
        return json_response(400, "轉出帳戶為必填項目")
    try:
        from_account_id = int(from_account_id_val)
    except (TypeError, ValueError):
        return json_response(400, "轉出帳戶 ID 必須為整數")

    to_account_id_val = body.get("to_account_id")
    if to_account_id_val is None:
        return json_response(400, "轉入帳戶為必填項目")
    try:
        to_account_id = int(to_account_id_val)
    except (TypeError, ValueError):
        return json_response(400, "轉入帳戶 ID 必須為整數")

    if from_account_id == to_account_id:
        return json_response(400, "轉出帳戶與轉入帳戶不能相同")

    from_account = db.session.get(Account, from_account_id)
    if not from_account:
        return json_response(400, "指定的轉出帳戶不存在")

    to_account = db.session.get(Account, to_account_id)
    if not to_account:
        return json_response(400, "指定的轉入帳戶不存在")

    note_val = body.get("note")
    note = str(note_val).strip() if note_val is not None else None

    try:
        transfer = Transfer(
            transferred_on=transferred_on,
            amount=amount,
            currency=currency,
            fx_rate_to_twd=fx_rate_to_twd,
            from_account_id=from_account_id,
            to_account_id=to_account_id,
            note=note,
        )
        db.session.add(transfer)
        db.session.commit()
        return json_response(201, "移轉建立成功", transfer.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


@transfers_bp.route("/<int:transfer_id>", methods=["GET"], strict_slashes=False)
def get_transfer(transfer_id: int):
    transfer = db.session.get(Transfer, transfer_id)
    if not transfer:
        return json_response(404, "找不到指定的移轉記錄")
    return json_response(200, "取得移轉成功", transfer.to_dict())
