from datetime import datetime, timezone

from extensions import db


class Account(db.Model):
    __tablename__ = "accounts"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    kind = db.Column(db.String(30), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="TWD", server_default="TWD")
    opening_balance = db.Column(db.Numeric(16, 4), nullable=False, default=0, server_default="0")
    statement_day = db.Column(db.Integer, nullable=True)
    payment_day = db.Column(db.Integer, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    __table_args__ = (
        db.CheckConstraint(
            "kind IN ('cash', 'bank', 'credit_card', 'broker')",
            name="ck_accounts_kind",
        ),
        db.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_accounts_currency",
        ),
        db.CheckConstraint(
            "statement_day IS NULL OR (statement_day >= 1 AND statement_day <= 31)",
            name="ck_accounts_statement_day",
        ),
        db.CheckConstraint(
            "payment_day IS NULL OR (payment_day >= 1 AND payment_day <= 31)",
            name="ck_accounts_payment_day",
        ),
    )

    def __repr__(self):
        return f"<Account id={self.id} name={self.name!r} kind={self.kind!r}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "kind": self.kind,
            "currency": self.currency,
            "opening_balance": float(self.opening_balance) if self.opening_balance is not None else 0.0,
            "statement_day": self.statement_day,
            "payment_day": self.payment_day,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Transfer(db.Model):
    __tablename__ = "transfers"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    transferred_on = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(16, 4), nullable=False)
    currency = db.Column(db.String(3), nullable=False)
    fx_rate_to_twd = db.Column(db.Numeric(12, 6), nullable=False)
    from_account_id = db.Column(
        db.BigInteger,
        db.ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    to_account_id = db.Column(
        db.BigInteger,
        db.ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    note = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    from_account = db.relationship(
        "Account",
        foreign_keys=[from_account_id],
        backref=db.backref("outgoing_transfers", lazy="select"),
    )
    to_account = db.relationship(
        "Account",
        foreign_keys=[to_account_id],
        backref=db.backref("incoming_transfers", lazy="select"),
    )

    __table_args__ = (
        db.CheckConstraint(
            "from_account_id <> to_account_id",
            name="ck_transfers_different_accounts",
        ),
        db.CheckConstraint(
            "amount > 0",
            name="ck_transfers_amount_positive",
        ),
        db.CheckConstraint(
            "fx_rate_to_twd > 0",
            name="ck_transfers_fx_rate_to_twd_positive",
        ),
        db.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_transfers_currency",
        ),
    )

    def __repr__(self):
        return (
            f"<Transfer id={self.id} on={self.transferred_on} "
            f"from={self.from_account_id} to={self.to_account_id} "
            f"amount={self.amount} {self.currency}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "transferred_on": self.transferred_on.isoformat() if self.transferred_on else None,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "currency": self.currency,
            "fx_rate_to_twd": float(self.fx_rate_to_twd) if self.fx_rate_to_twd is not None else 1.0,
            "from_account_id": self.from_account_id,
            "to_account_id": self.to_account_id,
            "note": self.note,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Invoice(db.Model):
    __tablename__ = "invoices"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    number = db.Column(db.String(10), nullable=False, unique=True)
    issued_on = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(16, 4), nullable=False)
    kind = db.Column(db.String(20), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="TWD", server_default="TWD")
    fx_rate_to_twd = db.Column(
        db.Numeric(12, 6),
        nullable=False,
        default=1.0,
        server_default="1.0",
    )
    random_code = db.Column(db.String(4), nullable=True)
    seller_name = db.Column(db.String(100), nullable=True)
    seller_ban = db.Column(db.String(8), nullable=True)
    prize_status = db.Column(
        db.String(20),
        nullable=False,
        default="unchecked",
        server_default="unchecked",
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    items = db.relationship(
        "InvoiceItem",
        backref=db.backref("invoice", lazy="select"),
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    __table_args__ = (
        db.CheckConstraint(
            "number ~ '^[A-Z]{2}[0-9]{8}$'",
            name="ck_invoices_number",
        ),
        db.CheckConstraint(
            "amount > 0",
            name="ck_invoices_amount_positive",
        ),
        db.CheckConstraint(
            "kind IN ('paper', 'electronic')",
            name="ck_invoices_kind",
        ),
        db.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_invoices_currency",
        ),
        db.CheckConstraint(
            "fx_rate_to_twd > 0",
            name="ck_invoices_fx_rate_to_twd_positive",
        ),
        db.CheckConstraint(
            "random_code IS NULL OR random_code ~ '^[0-9]{4}$'",
            name="ck_invoices_random_code",
        ),
        db.CheckConstraint(
            "seller_ban IS NULL OR seller_ban ~ '^[0-9]{8}$'",
            name="ck_invoices_seller_ban",
        ),
        db.CheckConstraint(
            "prize_status IN ('unchecked', 'lost', 'won', 'claimed', 'void')",
            name="ck_invoices_prize_status",
        ),
    )

    def __repr__(self):
        return f"<Invoice id={self.id} number={self.number!r} amount={self.amount}>"

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "issued_on": self.issued_on.isoformat() if self.issued_on else None,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "kind": self.kind,
            "currency": self.currency,
            "fx_rate_to_twd": float(self.fx_rate_to_twd) if self.fx_rate_to_twd is not None else 1.0,
            "random_code": self.random_code,
            "seller_name": self.seller_name,
            "seller_ban": self.seller_ban,
            "prize_status": self.prize_status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class InvoiceItem(db.Model):
    __tablename__ = "invoice_items"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    invoice_id = db.Column(
        db.BigInteger,
        db.ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    name = db.Column(db.String(200), nullable=False)
    quantity = db.Column(db.Numeric(12, 4), nullable=False)
    unit_price = db.Column(db.Numeric(16, 4), nullable=False)
    line_amount = db.Column(db.Numeric(16, 4), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    __table_args__ = (
        db.CheckConstraint(
            "quantity > 0",
            name="ck_invoice_items_quantity_positive",
        ),
        db.CheckConstraint(
            "unit_price > 0",
            name="ck_invoice_items_unit_price_positive",
        ),
        db.CheckConstraint(
            "line_amount > 0",
            name="ck_invoice_items_line_amount_positive",
        ),
    )

    def __repr__(self):
        return f"<InvoiceItem id={self.id} invoice_id={self.invoice_id} name={self.name!r}>"

    def to_dict(self):
        return {
            "id": self.id,
            "invoice_id": self.invoice_id,
            "name": self.name,
            "quantity": float(self.quantity) if self.quantity is not None else 0.0,
            "unit_price": float(self.unit_price) if self.unit_price is not None else 0.0,
            "line_amount": float(self.line_amount) if self.line_amount is not None else 0.0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DrawPeriod(db.Model):
    __tablename__ = "draw_periods"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    period_key = db.Column(db.String(20), nullable=False, unique=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    prizes = db.relationship(
        "DrawPrize",
        backref=db.backref("draw_period", lazy="select"),
        cascade="all, delete-orphan",
        passive_deletes=True,
    )

    def __repr__(self):
        return f"<DrawPeriod id={self.id} period_key={self.period_key!r}>"

    def to_dict(self):
        return {
            "id": self.id,
            "period_key": self.period_key,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class DrawPrize(db.Model):
    __tablename__ = "draw_prizes"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    draw_period_id = db.Column(
        db.BigInteger,
        db.ForeignKey("draw_periods.id", ondelete="CASCADE"),
        nullable=False,
    )
    tier = db.Column(db.String(20), nullable=False)
    matching_number = db.Column(db.String(20), nullable=False)
    amount = db.Column(db.Numeric(16, 4), nullable=False)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    __table_args__ = (
        db.UniqueConstraint(
            "draw_period_id",
            "tier",
            "matching_number",
            name="uq_draw_prizes_period_tier_number",
        ),
        db.CheckConstraint(
            "tier IN ('special', 'grand', 'first', 'second', 'third', 'fourth', 'fifth', 'sixth', 'extra_sixth')",
            name="ck_draw_prizes_tier",
        ),
        db.CheckConstraint(
            "amount >= 0",
            name="ck_draw_prizes_amount_non_negative",
        ),
    )

    def __repr__(self):
        return (
            f"<DrawPrize id={self.id} draw_period_id={self.draw_period_id} "
            f"tier={self.tier!r} matching_number={self.matching_number!r} amount={self.amount}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "draw_period_id": self.draw_period_id,
            "tier": self.tier,
            "matching_number": self.matching_number,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class IncomeCategory(db.Model):
    __tablename__ = "income_categories"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    incomes = db.relationship(
        "Income",
        backref=db.backref("category", lazy="select"),
        lazy="select",
    )

    def __repr__(self):
        return f"<IncomeCategory id={self.id} name={self.name!r}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Income(db.Model):
    __tablename__ = "incomes"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    received_on = db.Column(db.Date, nullable=False)
    amount = db.Column(db.Numeric(16, 4), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="TWD", server_default="TWD")
    fx_rate_to_twd = db.Column(
        db.Numeric(12, 6),
        nullable=False,
        default=1.0,
        server_default="1.0",
    )
    category_id = db.Column(
        db.BigInteger,
        db.ForeignKey("income_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id = db.Column(
        db.BigInteger,
        db.ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    source = db.Column(db.String(100), nullable=True)
    note = db.Column(db.Text, nullable=True)
    invoice_id = db.Column(
        db.BigInteger,
        db.ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    trade_id = db.Column(
        db.BigInteger,
        db.ForeignKey("trades.id", ondelete="RESTRICT"),
        nullable=True,
        unique=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    account = db.relationship(
        "Account",
        backref=db.backref("incomes", lazy="select"),
        lazy="select",
    )
    invoice = db.relationship(
        "Invoice",
        backref=db.backref("income", uselist=False, lazy="select", passive_deletes=True),
        lazy="select",
    )
    trade = db.relationship(
        "Trade",
        backref=db.backref("income", uselist=False, lazy="select", passive_deletes=True),
        lazy="select",
    )

    __table_args__ = (
        db.CheckConstraint(
            "amount > 0",
            name="ck_incomes_amount_positive",
        ),
        db.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_incomes_currency",
        ),
        db.CheckConstraint(
            "fx_rate_to_twd > 0",
            name="ck_incomes_fx_rate_to_twd_positive",
        ),
        db.CheckConstraint(
            "source IS NOT NULL OR note IS NOT NULL",
            name="ck_incomes_source_or_note_not_null",
        ),
    )

    def __repr__(self):
        return (
            f"<Income id={self.id} on={self.received_on} amount={self.amount} "
            f"account_id={self.account_id} category_id={self.category_id}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "received_on": self.received_on.isoformat() if self.received_on else None,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "currency": self.currency,
            "fx_rate_to_twd": float(self.fx_rate_to_twd) if self.fx_rate_to_twd is not None else 1.0,
            "category_id": self.category_id,
            "account_id": self.account_id,
            "source": self.source,
            "note": self.note,
            "invoice_id": self.invoice_id,
            "trade_id": self.trade_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ExpenseCategory(db.Model):
    __tablename__ = "expense_categories"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    name = db.Column(db.String(50), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    expenses = db.relationship(
        "Expense",
        backref=db.backref("category", lazy="select"),
        lazy="select",
    )

    def __repr__(self):
        return f"<ExpenseCategory id={self.id} name={self.name!r}>"

    def to_dict(self):
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Expense(db.Model):
    __tablename__ = "expenses"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    spent_on = db.Column(db.Date, nullable=False)
    settled_on = db.Column(db.Date, nullable=True)
    amount = db.Column(db.Numeric(16, 4), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="TWD", server_default="TWD")
    fx_rate_to_twd = db.Column(
        db.Numeric(12, 6),
        nullable=False,
        default=1.0,
        server_default="1.0",
    )
    category_id = db.Column(
        db.BigInteger,
        db.ForeignKey("expense_categories.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id = db.Column(
        db.BigInteger,
        db.ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    merchant = db.Column(db.String(100), nullable=True)
    note = db.Column(db.Text, nullable=True)
    invoice_id = db.Column(
        db.BigInteger,
        db.ForeignKey("invoices.id", ondelete="RESTRICT"),
        nullable=True,
    )
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    account = db.relationship(
        "Account",
        backref=db.backref("expenses", lazy="select"),
        lazy="select",
    )
    invoice = db.relationship(
        "Invoice",
        backref=db.backref("expenses", lazy="select", passive_deletes=True),
        lazy="select",
    )

    __table_args__ = (
        db.CheckConstraint(
            "amount > 0",
            name="ck_expenses_amount_positive",
        ),
        db.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_expenses_currency",
        ),
        db.CheckConstraint(
            "fx_rate_to_twd > 0",
            name="ck_expenses_fx_rate_to_twd_positive",
        ),
        db.CheckConstraint(
            "merchant IS NOT NULL OR note IS NOT NULL",
            name="ck_expenses_merchant_or_note_not_null",
        ),
    )

    def __repr__(self):
        return (
            f"<Expense id={self.id} on={self.spent_on} amount={self.amount} "
            f"account_id={self.account_id} category_id={self.category_id}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "spent_on": self.spent_on.isoformat() if self.spent_on else None,
            "settled_on": self.settled_on.isoformat() if self.settled_on else None,
            "amount": float(self.amount) if self.amount is not None else 0.0,
            "currency": self.currency,
            "fx_rate_to_twd": float(self.fx_rate_to_twd) if self.fx_rate_to_twd is not None else 1.0,
            "category_id": self.category_id,
            "account_id": self.account_id,
            "merchant": self.merchant,
            "note": self.note,
            "invoice_id": self.invoice_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Instrument(db.Model):
    __tablename__ = "instruments"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    market = db.Column(db.String(20), nullable=False)
    symbol = db.Column(db.String(20), nullable=False)
    name = db.Column(db.String(100), nullable=False)
    currency = db.Column(db.String(3), nullable=False, default="TWD", server_default="TWD")
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    trades = db.relationship(
        "Trade",
        backref=db.backref("instrument", lazy="select"),
        lazy="select",
    )

    __table_args__ = (
        db.UniqueConstraint("market", "symbol", name="uq_instruments_market_symbol"),
        db.CheckConstraint(
            "market IN ('tw_stock', 'us_stock', 'fund', 'other')",
            name="ck_instruments_market",
        ),
        db.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_instruments_currency",
        ),
    )

    def __repr__(self):
        return f"<Instrument id={self.id} market={self.market!r} symbol={self.symbol!r}>"

    def to_dict(self):
        return {
            "id": self.id,
            "market": self.market,
            "symbol": self.symbol,
            "name": self.name,
            "currency": self.currency,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Trade(db.Model):
    __tablename__ = "trades"

    id = db.Column(db.BigInteger, db.Identity(always=True), primary_key=True)
    instrument_id = db.Column(
        db.BigInteger,
        db.ForeignKey("instruments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id = db.Column(
        db.BigInteger,
        db.ForeignKey("accounts.id", ondelete="RESTRICT"),
        nullable=False,
    )
    trade_type = db.Column(db.String(30), nullable=False)
    traded_on = db.Column(db.Date, nullable=False)
    quantity = db.Column(db.Numeric(16, 6), nullable=True)
    price = db.Column(db.Numeric(16, 6), nullable=True)
    cash_amount = db.Column(db.Numeric(16, 4), nullable=True)
    ratio = db.Column(db.Numeric(12, 6), nullable=True)
    fee = db.Column(db.Numeric(16, 4), nullable=True, default=0, server_default="0")
    tax = db.Column(db.Numeric(16, 4), nullable=True, default=0, server_default="0")
    currency = db.Column(db.String(3), nullable=False, default="TWD", server_default="TWD")
    fx_rate_to_twd = db.Column(
        db.Numeric(12, 6),
        nullable=False,
        default=1.0,
        server_default="1.0",
    )
    voided_at = db.Column(db.DateTime(timezone=True), nullable=True)
    created_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )
    updated_at = db.Column(
        db.DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        server_default=db.text("(now() AT TIME ZONE 'utc')"),
    )

    account = db.relationship(
        "Account",
        backref=db.backref("trades", lazy="select"),
        lazy="select",
    )

    __table_args__ = (
        db.CheckConstraint(
            "trade_type IN ('buy', 'sell', 'cash_dividend', 'stock_dividend', 'drip', 'split', 'merge', 'capital_reduction')",
            name="ck_trades_trade_type",
        ),
        db.CheckConstraint(
            "quantity IS NULL OR quantity >= 0",
            name="ck_trades_quantity_non_negative",
        ),
        db.CheckConstraint(
            "price IS NULL OR price >= 0",
            name="ck_trades_price_non_negative",
        ),
        db.CheckConstraint(
            "ratio IS NULL OR ratio > 0",
            name="ck_trades_ratio_positive",
        ),
        db.CheckConstraint(
            "fee IS NULL OR fee >= 0",
            name="ck_trades_fee_non_negative",
        ),
        db.CheckConstraint(
            "tax IS NULL OR tax >= 0",
            name="ck_trades_tax_non_negative",
        ),
        db.CheckConstraint(
            "currency ~ '^[A-Z]{3}$'",
            name="ck_trades_currency",
        ),
        db.CheckConstraint(
            "fx_rate_to_twd > 0",
            name="ck_trades_fx_rate_to_twd_positive",
        ),
    )

    def __repr__(self):
        return (
            f"<Trade id={self.id} on={self.traded_on} type={self.trade_type!r} "
            f"instrument_id={self.instrument_id} account_id={self.account_id}>"
        )

    def to_dict(self):
        return {
            "id": self.id,
            "instrument_id": self.instrument_id,
            "account_id": self.account_id,
            "trade_type": self.trade_type,
            "traded_on": self.traded_on.isoformat() if self.traded_on else None,
            "quantity": float(self.quantity) if self.quantity is not None else None,
            "price": float(self.price) if self.price is not None else None,
            "cash_amount": float(self.cash_amount) if self.cash_amount is not None else None,
            "ratio": float(self.ratio) if self.ratio is not None else None,
            "fee": float(self.fee) if self.fee is not None else None,
            "tax": float(self.tax) if self.tax is not None else None,
            "currency": self.currency,
            "fx_rate_to_twd": float(self.fx_rate_to_twd) if self.fx_rate_to_twd is not None else 1.0,
            "voided_at": self.voided_at.isoformat() if self.voided_at else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
