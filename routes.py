from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, request
from sqlalchemy.exc import IntegrityError, OperationalError

from extensions import db
from models import (
    Account,
    Transfer,
    IncomeCategory,
    Income,
    Invoice,
    ExpenseCategory,
    Expense,
)
from utils import json_response

ALLOWED_ACCOUNT_KINDS = {"cash", "bank", "credit_card", "broker"}

accounts_bp = Blueprint("accounts", __name__, url_prefix="/api/accounts")
transfers_bp = Blueprint("transfers", __name__, url_prefix="/api/transfers")
income_categories_bp = Blueprint("income_categories", __name__, url_prefix="/api/income-categories")
incomes_bp = Blueprint("incomes", __name__, url_prefix="/api/incomes")
expense_categories_bp = Blueprint("expense_categories", __name__, url_prefix="/api/expense-categories")
expenses_bp = Blueprint("expenses", __name__, url_prefix="/api/expenses")


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
    incomes = Income.query.filter_by(account_id=account.id).all()
    expenses = Expense.query.filter_by(account_id=account.id).all()

    # 原幣別餘額：期初餘額 + 轉入 - 轉出 + 入帳 - 花費
    orig_in = sum((Decimal(str(t.amount)) for t in transfers_in), Decimal("0"))
    orig_out = sum((Decimal(str(t.amount)) for t in transfers_out), Decimal("0"))
    orig_income = sum((Decimal(str(i.amount)) for i in incomes), Decimal("0"))
    orig_expense = sum((Decimal(str(e.amount)) for e in expenses), Decimal("0"))
    original_balance = opening + orig_in - orig_out + orig_income - orig_expense

    # 台幣餘額：轉入轉出、入帳與花費金額先乘上該列的 fx_rate_to_twd
    twd_in = sum(
        (Decimal(str(t.amount)) * Decimal(str(t.fx_rate_to_twd)) for t in transfers_in),
        Decimal("0"),
    )
    twd_out = sum(
        (Decimal(str(t.amount)) * Decimal(str(t.fx_rate_to_twd)) for t in transfers_out),
        Decimal("0"),
    )
    twd_income = sum(
        (Decimal(str(i.amount)) * Decimal(str(i.fx_rate_to_twd)) for i in incomes),
        Decimal("0"),
    )
    twd_expense = sum(
        (Decimal(str(e.amount)) * Decimal(str(e.fx_rate_to_twd)) for e in expenses),
        Decimal("0"),
    )
    twd_balance = opening + twd_in - twd_out + twd_income - twd_expense

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


# ==========================================
# 入帳分類路由 Income Categories Routes
# ==========================================

@income_categories_bp.route("", methods=["GET"], strict_slashes=False)
def list_income_categories():
    categories = IncomeCategory.query.order_by(IncomeCategory.id.asc()).all()
    return json_response(200, "取得入帳分類清單成功", [c.to_dict() for c in categories])


@income_categories_bp.route("", methods=["POST"], strict_slashes=False)
def create_income_category():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    name_val = body.get("name")
    if name_val is None or str(name_val).strip() == "":
        return json_response(400, "分類名稱為必填項目")
    name = str(name_val).strip()

    existing = IncomeCategory.query.filter_by(name=name).first()
    if existing:
        return json_response(400, "分類名稱已被使用，請使用其他名稱")

    desc_val = body.get("description")
    description = str(desc_val).strip() if desc_val is not None and str(desc_val).strip() != "" else None

    try:
        category = IncomeCategory(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        return json_response(201, "入帳分類建立成功", category.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


@income_categories_bp.route("/<int:category_id>", methods=["GET"], strict_slashes=False)
def get_income_category(category_id: int):
    category = db.session.get(IncomeCategory, category_id)
    if not category:
        return json_response(404, "找不到指定的入帳分類")
    return json_response(200, "取得入帳分類成功", category.to_dict())


@income_categories_bp.route("/<int:category_id>", methods=["PATCH"], strict_slashes=False)
def update_income_category(category_id: int):
    category = db.session.get(IncomeCategory, category_id)
    if not category:
        return json_response(404, "找不到指定的入帳分類")

    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    if "name" in body:
        name_val = body.get("name")
        if name_val is None or str(name_val).strip() == "":
            return json_response(400, "分類名稱不能為空")
        new_name = str(name_val).strip()
        existing = IncomeCategory.query.filter(
            IncomeCategory.name == new_name,
            IncomeCategory.id != category_id,
        ).first()
        if existing:
            return json_response(400, "分類名稱已被使用，請使用其他名稱")
        category.name = new_name

    if "description" in body:
        desc_val = body.get("description")
        category.description = str(desc_val).strip() if desc_val is not None and str(desc_val).strip() != "" else None

    category.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return json_response(200, "入帳分類更新成功", category.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


# ==========================================
# 入帳路由 Incomes Routes
# ==========================================

@incomes_bp.route("", methods=["GET"], strict_slashes=False)
def list_incomes():
    query = Income.query

    if "account_id" in request.args:
        try:
            acc_id = int(request.args.get("account_id"))
            query = query.filter(Income.account_id == acc_id)
        except (TypeError, ValueError):
            return json_response(400, "帳戶 ID 必須為整數")

    if "category_id" in request.args:
        try:
            cat_id = int(request.args.get("category_id"))
            query = query.filter(Income.category_id == cat_id)
        except (TypeError, ValueError):
            return json_response(400, "分類 ID 必須為整數")

    if "date_from" in request.args:
        date_from_val = request.args.get("date_from", "").strip()
        if date_from_val != "":
            try:
                d_from = datetime.strptime(date_from_val, "%Y-%m-%d").date()
                query = query.filter(Income.received_on >= d_from)
            except ValueError:
                return json_response(400, "起始日期格式不正確，請使用 YYYY-MM-DD 格式")

    if "date_to" in request.args:
        date_to_val = request.args.get("date_to", "").strip()
        if date_to_val != "":
            try:
                d_to = datetime.strptime(date_to_val, "%Y-%m-%d").date()
                query = query.filter(Income.received_on <= d_to)
            except ValueError:
                return json_response(400, "結束日期格式不正確，請使用 YYYY-MM-DD 格式")

    incomes = query.order_by(Income.received_on.desc(), Income.id.desc()).all()
    return json_response(200, "取得入帳清單成功", [i.to_dict() for i in incomes])


@incomes_bp.route("", methods=["POST"], strict_slashes=False)
def create_income():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    received_on_val = body.get("received_on")
    if received_on_val is None or str(received_on_val).strip() == "":
        return json_response(400, "入帳日期為必填項目")
    try:
        received_on = datetime.strptime(str(received_on_val).strip(), "%Y-%m-%d").date()
    except ValueError:
        return json_response(400, "日期格式不正確，請使用 YYYY-MM-DD 格式")

    amount_val = body.get("amount")
    if amount_val is None:
        return json_response(400, "入帳金額為必填項目")
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

    cat_id_val = body.get("category_id")
    if cat_id_val is None:
        return json_response(400, "入帳分類為必填項目")
    try:
        category_id = int(cat_id_val)
    except (TypeError, ValueError):
        return json_response(400, "分類 ID 必須為整數")

    category = db.session.get(IncomeCategory, category_id)
    if not category:
        return json_response(400, "指定的入帳分類不存在")

    acc_id_val = body.get("account_id")
    if acc_id_val is None:
        return json_response(400, "帳戶為必填項目")
    try:
        account_id = int(acc_id_val)
    except (TypeError, ValueError):
        return json_response(400, "帳戶 ID 必須為整數")

    account = db.session.get(Account, account_id)
    if not account:
        return json_response(400, "指定的帳戶不存在")

    source_val = body.get("source")
    source = str(source_val).strip() if source_val is not None and str(source_val).strip() != "" else None

    note_val = body.get("note")
    note = str(note_val).strip() if note_val is not None and str(note_val).strip() != "" else None

    if source is None and note is None:
        return json_response(400, "來源與備註不可同時為空，至少需填寫一項")

    invoice_id = None
    if "invoice_id" in body and body["invoice_id"] is not None:
        try:
            invoice_id = int(body["invoice_id"])
        except (TypeError, ValueError):
            return json_response(400, "發票 ID 必須為整數")

        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            return json_response(400, "指定的發票不存在")

        existing_inv = Income.query.filter_by(invoice_id=invoice_id).first()
        if existing_inv:
            return json_response(400, "此發票已綁定過入帳紀錄")

    try:
        income = Income(
            received_on=received_on,
            amount=amount,
            currency=currency,
            fx_rate_to_twd=fx_rate_to_twd,
            category_id=category_id,
            account_id=account_id,
            source=source,
            note=note,
            invoice_id=invoice_id,
        )
        db.session.add(income)
        db.session.commit()
        return json_response(201, "入帳建立成功", income.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


@incomes_bp.route("/<int:income_id>", methods=["GET"], strict_slashes=False)
def get_income(income_id: int):
    income = db.session.get(Income, income_id)
    if not income:
        return json_response(404, "找不到指定的入帳記錄")
    return json_response(200, "取得入帳記錄成功", income.to_dict())


@incomes_bp.route("/<int:income_id>", methods=["PATCH"], strict_slashes=False)
def update_income(income_id: int):
    income = db.session.get(Income, income_id)
    if not income:
        return json_response(404, "找不到指定的入帳記錄")

    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    if "received_on" in body:
        val = body.get("received_on")
        if val is None or str(val).strip() == "":
            return json_response(400, "入帳日期不能為空")
        try:
            income.received_on = datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
        except ValueError:
            return json_response(400, "日期格式不正確，請使用 YYYY-MM-DD 格式")

    if "amount" in body:
        val = body.get("amount")
        if val is None:
            return json_response(400, "金額不能為空")
        try:
            amt = Decimal(str(val))
            if amt <= 0:
                return json_response(400, "金額必須大於 0")
            income.amount = amt
        except (InvalidOperation, TypeError, ValueError):
            return json_response(400, "金額格式不正確，必須為正數")

    if "currency" in body:
        val = body.get("currency")
        if val is None or str(val).strip() == "":
            return json_response(400, "幣別不能為空")
        cur = str(val).strip().upper()
        if len(cur) != 3 or not cur.isalpha():
            return json_response(400, "幣別代碼必須為 3 碼英文字母")
        income.currency = cur

    if "fx_rate_to_twd" in body:
        val = body.get("fx_rate_to_twd")
        if val is None:
            return json_response(400, "匯率不能為空")
        try:
            fx = Decimal(str(val))
            if fx <= 0:
                return json_response(400, "匯率必須大於 0")
            income.fx_rate_to_twd = fx
        except (InvalidOperation, TypeError, ValueError):
            return json_response(400, "匯率格式不正確，必須為正數")

    if "category_id" in body:
        val = body.get("category_id")
        if val is None:
            return json_response(400, "分類不能為空")
        try:
            cat_id = int(val)
        except (TypeError, ValueError):
            return json_response(400, "分類 ID 必須為整數")
        cat = db.session.get(IncomeCategory, cat_id)
        if not cat:
            return json_response(400, "指定的入帳分類不存在")
        income.category_id = cat_id

    if "account_id" in body:
        val = body.get("account_id")
        if val is None:
            return json_response(400, "帳戶不能為空")
        try:
            acc_id = int(val)
        except (TypeError, ValueError):
            return json_response(400, "帳戶 ID 必須為整數")
        acc = db.session.get(Account, acc_id)
        if not acc:
            return json_response(400, "指定的帳戶不存在")
        income.account_id = acc_id

    # 處理 source 與 note，兩者不可同時為空
    if "source" in body or "note" in body:
        if "source" in body:
            s_val = body.get("source")
            new_source = str(s_val).strip() if s_val is not None and str(s_val).strip() != "" else None
        else:
            new_source = income.source

        if "note" in body:
            n_val = body.get("note")
            new_note = str(n_val).strip() if n_val is not None and str(n_val).strip() != "" else None
        else:
            new_note = income.note

        if new_source is None and new_note is None:
            return json_response(400, "來源與備註不可同時為空，至少需填寫一項")

        income.source = new_source
        income.note = new_note

    # 改 updated_at
    income.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return json_response(200, "入帳記錄更新成功", income.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


# ==========================================
# 花費分類路由 Expense Categories Routes
# ==========================================

@expense_categories_bp.route("", methods=["GET"], strict_slashes=False)
def list_expense_categories():
    categories = ExpenseCategory.query.order_by(ExpenseCategory.id.asc()).all()
    return json_response(200, "取得花費分類清單成功", [c.to_dict() for c in categories])


@expense_categories_bp.route("", methods=["POST"], strict_slashes=False)
def create_expense_category():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    name_val = body.get("name")
    if name_val is None or str(name_val).strip() == "":
        return json_response(400, "分類名稱為必填項目")
    name = str(name_val).strip()

    existing = ExpenseCategory.query.filter_by(name=name).first()
    if existing:
        return json_response(400, "分類名稱已被使用，請使用其他名稱")

    desc_val = body.get("description")
    description = str(desc_val).strip() if desc_val is not None and str(desc_val).strip() != "" else None

    try:
        category = ExpenseCategory(name=name, description=description)
        db.session.add(category)
        db.session.commit()
        return json_response(201, "花費分類建立成功", category.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


@expense_categories_bp.route("/<int:category_id>", methods=["GET"], strict_slashes=False)
def get_expense_category(category_id: int):
    category = db.session.get(ExpenseCategory, category_id)
    if not category:
        return json_response(404, "找不到指定的花費分類")
    return json_response(200, "取得花費分類成功", category.to_dict())


@expense_categories_bp.route("/<int:category_id>", methods=["PATCH"], strict_slashes=False)
def update_expense_category(category_id: int):
    category = db.session.get(ExpenseCategory, category_id)
    if not category:
        return json_response(404, "找不到指定的花費分類")

    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    if "name" in body:
        name_val = body.get("name")
        if name_val is None or str(name_val).strip() == "":
            return json_response(400, "分類名稱不能為空")
        new_name = str(name_val).strip()
        existing = ExpenseCategory.query.filter(
            ExpenseCategory.name == new_name,
            ExpenseCategory.id != category_id,
        ).first()
        if existing:
            return json_response(400, "分類名稱已被使用，請使用其他名稱")
        category.name = new_name

    if "description" in body:
        desc_val = body.get("description")
        category.description = str(desc_val).strip() if desc_val is not None and str(desc_val).strip() != "" else None

    category.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return json_response(200, "花費分類更新成功", category.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


# ==========================================
# 花費路由 Expenses Routes
# ==========================================

@expenses_bp.route("", methods=["GET"], strict_slashes=False)
def list_expenses():
    query = Expense.query

    if "account_id" in request.args:
        try:
            acc_id = int(request.args.get("account_id"))
            query = query.filter(Expense.account_id == acc_id)
        except (TypeError, ValueError):
            return json_response(400, "帳戶 ID 必須為整數")

    if "category_id" in request.args:
        try:
            cat_id = int(request.args.get("category_id"))
            query = query.filter(Expense.category_id == cat_id)
        except (TypeError, ValueError):
            return json_response(400, "分類 ID 必須為整數")

    if "invoice_id" in request.args:
        try:
            inv_id = int(request.args.get("invoice_id"))
            query = query.filter(Expense.invoice_id == inv_id)
        except (TypeError, ValueError):
            return json_response(400, "發票 ID 必須為整數")

    if "date_from" in request.args:
        date_from_val = request.args.get("date_from", "").strip()
        if date_from_val != "":
            try:
                d_from = datetime.strptime(date_from_val, "%Y-%m-%d").date()
                query = query.filter(Expense.spent_on >= d_from)
            except ValueError:
                return json_response(400, "起始日期格式不正確，請使用 YYYY-MM-DD 格式")

    if "date_to" in request.args:
        date_to_val = request.args.get("date_to", "").strip()
        if date_to_val != "":
            try:
                d_to = datetime.strptime(date_to_val, "%Y-%m-%d").date()
                query = query.filter(Expense.spent_on <= d_to)
            except ValueError:
                return json_response(400, "結束日期格式不正確，請使用 YYYY-MM-DD 格式")

    expenses = query.order_by(Expense.spent_on.desc(), Expense.id.desc()).all()
    return json_response(200, "取得花費清單成功", [e.to_dict() for e in expenses])


@expenses_bp.route("", methods=["POST"], strict_slashes=False)
def create_expense():
    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    spent_on_val = body.get("spent_on")
    if spent_on_val is None or str(spent_on_val).strip() == "":
        return json_response(400, "消費日期為必填項目")
    try:
        spent_on = datetime.strptime(str(spent_on_val).strip(), "%Y-%m-%d").date()
    except ValueError:
        return json_response(400, "消費日期格式不正確，請使用 YYYY-MM-DD 格式")

    settled_on = None
    if "settled_on" in body and body["settled_on"] is not None and str(body["settled_on"]).strip() != "":
        try:
            settled_on = datetime.strptime(str(body["settled_on"]).strip(), "%Y-%m-%d").date()
        except ValueError:
            return json_response(400, "扣款日期格式不正確，請使用 YYYY-MM-DD 格式")

    amount_val = body.get("amount")
    if amount_val is None:
        return json_response(400, "花費金額為必填項目")
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

    cat_id_val = body.get("category_id")
    if cat_id_val is None:
        return json_response(400, "花費分類為必填項目")
    try:
        category_id = int(cat_id_val)
    except (TypeError, ValueError):
        return json_response(400, "分類 ID 必須為整數")

    category = db.session.get(ExpenseCategory, category_id)
    if not category:
        return json_response(400, "指定的花費分類不存在")

    acc_id_val = body.get("account_id")
    if acc_id_val is None:
        return json_response(400, "帳戶為必填項目")
    try:
        account_id = int(acc_id_val)
    except (TypeError, ValueError):
        return json_response(400, "帳戶 ID 必須為整數")

    account = db.session.get(Account, account_id)
    if not account:
        return json_response(400, "指定的帳戶不存在")

    merchant_val = body.get("merchant")
    merchant = str(merchant_val).strip() if merchant_val is not None and str(merchant_val).strip() != "" else None

    note_val = body.get("note")
    note = str(note_val).strip() if note_val is not None and str(note_val).strip() != "" else None

    if merchant is None and note is None:
        return json_response(400, "商家與備註不可同時為空，至少需填寫一項")

    invoice_id = None
    if "invoice_id" in body and body["invoice_id"] is not None:
        try:
            invoice_id = int(body["invoice_id"])
        except (TypeError, ValueError):
            return json_response(400, "發票 ID 必須為整數")

        invoice = db.session.get(Invoice, invoice_id)
        if not invoice:
            return json_response(400, "指定的發票不存在")

    try:
        expense = Expense(
            spent_on=spent_on,
            settled_on=settled_on,
            amount=amount,
            currency=currency,
            fx_rate_to_twd=fx_rate_to_twd,
            category_id=category_id,
            account_id=account_id,
            merchant=merchant,
            note=note,
            invoice_id=invoice_id,
        )
        db.session.add(expense)
        db.session.commit()
        return json_response(201, "花費建立成功", expense.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")


@expenses_bp.route("/<int:expense_id>", methods=["GET"], strict_slashes=False)
def get_expense(expense_id: int):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        return json_response(404, "找不到指定的花費記錄")
    return json_response(200, "取得花費記錄成功", expense.to_dict())


@expenses_bp.route("/<int:expense_id>", methods=["PATCH"], strict_slashes=False)
def update_expense(expense_id: int):
    expense = db.session.get(Expense, expense_id)
    if not expense:
        return json_response(404, "找不到指定的花費記錄")

    body = request.get_json(silent=True)
    if body is None or not isinstance(body, dict):
        return json_response(400, "請求內容必須是有效的 JSON 格式")

    if "spent_on" in body:
        val = body.get("spent_on")
        if val is None or str(val).strip() == "":
            return json_response(400, "消費日期不能為空")
        try:
            expense.spent_on = datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
        except ValueError:
            return json_response(400, "消費日期格式不正確，請使用 YYYY-MM-DD 格式")

    if "settled_on" in body:
        val = body.get("settled_on")
        if val is None or str(val).strip() == "":
            expense.settled_on = None
        else:
            try:
                expense.settled_on = datetime.strptime(str(val).strip(), "%Y-%m-%d").date()
            except ValueError:
                return json_response(400, "扣款日期格式不正確，請使用 YYYY-MM-DD 格式")

    if "amount" in body:
        val = body.get("amount")
        if val is None:
            return json_response(400, "金額不能為空")
        try:
            amt = Decimal(str(val))
            if amt <= 0:
                return json_response(400, "金額必須大於 0")
            expense.amount = amt
        except (InvalidOperation, TypeError, ValueError):
            return json_response(400, "金額格式不正確，必須為正數")

    if "currency" in body:
        val = body.get("currency")
        if val is None or str(val).strip() == "":
            return json_response(400, "幣別不能為空")
        cur = str(val).strip().upper()
        if len(cur) != 3 or not cur.isalpha():
            return json_response(400, "幣別代碼必須為 3 碼英文字母")
        expense.currency = cur

    if "fx_rate_to_twd" in body:
        val = body.get("fx_rate_to_twd")
        if val is None:
            return json_response(400, "匯率不能為空")
        try:
            fx = Decimal(str(val))
            if fx <= 0:
                return json_response(400, "匯率必須大於 0")
            expense.fx_rate_to_twd = fx
        except (InvalidOperation, TypeError, ValueError):
            return json_response(400, "匯率格式不正確，必須為正數")

    if "category_id" in body:
        val = body.get("category_id")
        if val is None:
            return json_response(400, "分類不能為空")
        try:
            cat_id = int(val)
        except (TypeError, ValueError):
            return json_response(400, "分類 ID 必須為整數")
        cat = db.session.get(ExpenseCategory, cat_id)
        if not cat:
            return json_response(400, "指定的花費分類不存在")
        expense.category_id = cat_id

    if "account_id" in body:
        val = body.get("account_id")
        if val is None:
            return json_response(400, "帳戶不能為空")
        try:
            acc_id = int(val)
        except (TypeError, ValueError):
            return json_response(400, "帳戶 ID 必須為整數")
        acc = db.session.get(Account, acc_id)
        if not acc:
            return json_response(400, "指定的帳戶不存在")
        expense.account_id = acc_id

    if "invoice_id" in body:
        val = body.get("invoice_id")
        if val is None or str(val).strip() == "":
            expense.invoice_id = None
        else:
            try:
                inv_id = int(val)
            except (TypeError, ValueError):
                return json_response(400, "發票 ID 必須為整數")
            inv = db.session.get(Invoice, inv_id)
            if not inv:
                return json_response(400, "指定的發票不存在")
            expense.invoice_id = inv_id

    # 處理 merchant 與 note，兩者不可同時為空
    if "merchant" in body or "note" in body:
        if "merchant" in body:
            m_val = body.get("merchant")
            new_merchant = str(m_val).strip() if m_val is not None and str(m_val).strip() != "" else None
        else:
            new_merchant = expense.merchant

        if "note" in body:
            n_val = body.get("note")
            new_note = str(n_val).strip() if n_val is not None and str(n_val).strip() != "" else None
        else:
            new_note = expense.note

        if new_merchant is None and new_note is None:
            return json_response(400, "商家與備註不可同時為空，至少需填寫一項")

        expense.merchant = new_merchant
        expense.note = new_note

    # 改 updated_at
    expense.updated_at = datetime.now(timezone.utc)

    try:
        db.session.commit()
        return json_response(200, "花費記錄更新成功", expense.to_dict())
    except IntegrityError:
        db.session.rollback()
        return json_response(400, "資料格式不合法或違反約束條件")
    except OperationalError:
        db.session.rollback()
        return json_response(500, "資料庫連線失敗，請稍後再試")
    except Exception:
        db.session.rollback()
        return json_response(500, "伺服器內部錯誤")
