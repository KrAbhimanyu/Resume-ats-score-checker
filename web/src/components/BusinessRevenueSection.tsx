import React, { FormEvent, useCallback, useEffect, useState } from 'react';
import { ArrowRight, BadgePercent, BriefcaseBusiness, CreditCard, Gift, ShieldCheck, Store, Wallet } from 'lucide-react';
import { careerRequest } from '../services/careerApi';

type BusinessRecord = Record<string, unknown>;

interface RazorpayCheckoutResult {
  razorpay_order_id?: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
  razorpay_subscription_id?: string;
}

interface RazorpayOptions {
  key: string;
  amount?: number;
  currency?: string;
  name: string;
  description: string;
  order_id?: string;
  subscription_id?: string;
  handler: (result: RazorpayCheckoutResult) => void;
  modal?: { ondismiss?: () => void };
  theme?: { color: string };
}

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayOptions) => { open: () => void };
  }
}

const objectValue = (value: unknown): BusinessRecord =>
  value && typeof value === 'object' && !Array.isArray(value) ? value as BusinessRecord : {};

const arrayValue = (value: unknown): BusinessRecord[] =>
  Array.isArray(value) ? value.map(objectValue) : [];

const formatMoney = (minor: unknown, currency: unknown): string => {
  if (typeof minor !== 'number' || typeof currency !== 'string') return 'Price unavailable';
  return new Intl.NumberFormat(undefined, { style: 'currency', currency }).format(minor / 100);
};

const formatDate = (value: unknown): string => {
  if (typeof value !== 'string' || !value) return '—';
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleDateString();
};

const checkoutScript = 'https://checkout.razorpay.com/v1/checkout.js';

async function openRazorpay(options: RazorpayOptions): Promise<void> {
  if (!window.Razorpay) {
    await new Promise<void>((resolve, reject) => {
      const existing = document.querySelector<HTMLScriptElement>(`script[src="${checkoutScript}"]`);
      if (existing?.dataset.loaded === 'true') {
        resolve();
        return;
      }
      const script = existing || document.createElement('script');
      const onLoad = () => {
        script.dataset.loaded = 'true';
        cleanup();
        resolve();
      };
      const onError = () => {
        cleanup();
        reject(new Error('Razorpay Checkout could not be loaded. Check your connection and try again.'));
      };
      const cleanup = () => {
        script.removeEventListener('load', onLoad);
        script.removeEventListener('error', onError);
      };
      script.addEventListener('load', onLoad);
      script.addEventListener('error', onError);
      if (!existing) {
        script.src = checkoutScript;
        script.async = true;
        document.body.appendChild(script);
      }
    });
  }
  if (!window.Razorpay) throw new Error('Razorpay Checkout did not initialize.');
  new window.Razorpay(options).open();
}

export const BusinessRevenueSection: React.FC<{ token: string }> = ({ token }) => {
  const [status, setStatus] = useState<BusinessRecord>({});
  const [plans, setPlans] = useState<BusinessRecord[]>([]);
  const [entitlements, setEntitlements] = useState<BusinessRecord>({});
  const [credits, setCredits] = useState<BusinessRecord>({});
  const [transactions, setTransactions] = useState<BusinessRecord[]>([]);
  const [subscriptions, setSubscriptions] = useState<BusinessRecord[]>([]);
  const [referrals, setReferrals] = useState<BusinessRecord>({});
  const [affiliate, setAffiliate] = useState<BusinessRecord>({});
  const [leads, setLeads] = useState<BusinessRecord[]>([]);
  const [listings, setListings] = useState<BusinessRecord[]>([]);
  const [orders, setOrders] = useState<BusinessRecord[]>([]);
  const [adminOverview, setAdminOverview] = useState<BusinessRecord>({});
  const [adminPricing, setAdminPricing] = useState<BusinessRecord[]>([]);
  const [adminSettings, setAdminSettings] = useState<BusinessRecord>({});
  const [adminTransactions, setAdminTransactions] = useState<BusinessRecord[]>([]);
  const [adminLeads, setAdminLeads] = useState<BusinessRecord[]>([]);
  const [adminAffiliates, setAdminAffiliates] = useState<BusinessRecord[]>([]);
  const [adminConversions, setAdminConversions] = useState<BusinessRecord[]>([]);
  const [adminListings, setAdminListings] = useState<BusinessRecord[]>([]);
  const [adminCoupons, setAdminCoupons] = useState<BusinessRecord[]>([]);
  const [error, setError] = useState('');
  const [notice, setNotice] = useState('');
  const [busy, setBusy] = useState(false);
  const [couponCode, setCouponCode] = useState('');
  const [claimCode, setClaimCode] = useState('');
  const [leadType, setLeadType] = useState('student');
  const [organization, setOrganization] = useState('');
  const [leadDetails, setLeadDetails] = useState('');
  const [listingType, setListingType] = useState('resume_review');
  const [listingTitle, setListingTitle] = useState('');
  const [listingDescription, setListingDescription] = useState('');
  const [listingPrice, setListingPrice] = useState('');
  const [listingCurrency, setListingCurrency] = useState('INR');
  const [orderRequirements, setOrderRequirements] = useState<Record<string, string>>({});
  const [newPlan, setNewPlan] = useState({
    id: '', name: '', tier: 'starter', billing_interval: 'monthly', price_minor: '',
    currency: 'INR', credits_grant: '0', entitlements: '{\n  "career_workspace": true\n}',
  });
  const [couponForm, setCouponForm] = useState({
    code: '', discount_type: 'percent', discount_value: '', currency: 'INR',
    max_redemptions: '', expires_at: '',
  });

  const load = useCallback(async () => {
    setError('');
    try {
      const [
        nextStatus, nextPlans, nextEntitlements, nextCredits, nextTransactions, nextSubscriptions,
        nextReferrals, nextAffiliate, nextLeads, nextListings, nextOrders,
      ] = await Promise.all([
        careerRequest<BusinessRecord>(token, '/business/status'),
        careerRequest<BusinessRecord[]>(token, '/business/plans'),
        careerRequest<BusinessRecord>(token, '/business/entitlements'),
        careerRequest<BusinessRecord>(token, '/business/credits'),
        careerRequest<BusinessRecord[]>(token, '/business/transactions'),
        careerRequest<BusinessRecord[]>(token, '/business/subscriptions'),
        careerRequest<BusinessRecord>(token, '/business/referrals'),
        careerRequest<BusinessRecord>(token, '/business/affiliates'),
        careerRequest<BusinessRecord[]>(token, '/business/leads'),
        careerRequest<BusinessRecord[]>(token, '/business/marketplace'),
        careerRequest<BusinessRecord[]>(token, '/business/marketplace/orders'),
      ]);
      setStatus(nextStatus);
      setPlans(nextPlans);
      setEntitlements(nextEntitlements);
      setCredits(nextCredits);
      setTransactions(nextTransactions);
      setSubscriptions(nextSubscriptions);
      setReferrals(nextReferrals);
      setAffiliate(nextAffiliate);
      setLeads(nextLeads);
      setListings(nextListings);
      setOrders(nextOrders);
      if (nextStatus.admin) {
        const [overview, pricing, settings, allTransactions, allLeads, allAffiliates, conversions, pendingListings, coupons] = await Promise.all([
          careerRequest<BusinessRecord>(token, '/business/admin/overview'),
          careerRequest<BusinessRecord[]>(token, '/business/admin/ai-pricing'),
          careerRequest<BusinessRecord>(token, '/business/admin/settings'),
          careerRequest<BusinessRecord[]>(token, '/business/admin/transactions'),
          careerRequest<BusinessRecord[]>(token, '/business/admin/leads'),
          careerRequest<BusinessRecord[]>(token, '/business/admin/affiliates'),
          careerRequest<BusinessRecord[]>(token, '/business/admin/affiliate-conversions'),
          careerRequest<BusinessRecord[]>(token, '/business/admin/marketplace/listings'),
          careerRequest<BusinessRecord[]>(token, '/business/admin/coupons'),
        ]);
        setAdminOverview(overview);
        setAdminPricing(pricing);
        setAdminSettings(settings);
        setAdminTransactions(allTransactions);
        setAdminLeads(allLeads);
        setAdminAffiliates(allAffiliates);
        setAdminConversions(conversions);
        setAdminListings(pendingListings);
        setAdminCoupons(coupons);
      }
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Business account information could not be loaded.');
    }
  }, [token]);

  useEffect(() => { void load(); }, [load]);
  useEffect(() => {
    const referralCode = new URLSearchParams(window.location.search).get('ref');
    if (referralCode) setClaimCode(referralCode);
  }, []);
  useEffect(() => {
    const url = new URL(window.location.href);
    const sessionId = url.searchParams.get('business_checkout_session');
    const checkoutCancelled = url.searchParams.has('business_checkout_cancelled');
    if (!sessionId) {
      if (checkoutCancelled) {
        url.searchParams.delete('business_checkout_cancelled');
        window.history.replaceState({}, '', url);
        setNotice('Checkout was cancelled; no payment was confirmed.');
      }
      return;
    }
    window.history.replaceState({}, '', url);
    let active = true;
    setBusy(true);
    setError('');
    careerRequest(token, '/business/stripe/checkout/verify', {
      method: 'POST',
      body: { session_id: sessionId },
    }).then(async () => {
      if (!active) return;
      setNotice('Stripe confirmed your payment.');
      await load();
    }).catch((requestError) => {
      if (active) {
        setError(requestError instanceof Error ? requestError.message : 'Stripe checkout could not be verified.');
      }
    }).finally(() => {
      if (active) {
        const cleanUrl = new URL(window.location.href);
        cleanUrl.searchParams.delete('business_checkout_session');
        cleanUrl.searchParams.delete('business_checkout_cancelled');
        window.history.replaceState({}, '', cleanUrl);
        setBusy(false);
      }
    });
    return () => { active = false; };
  }, [token, load]);

  const run = async (action: () => Promise<unknown>, success?: string) => {
    setBusy(true);
    setError('');
    setNotice('');
    try {
      await action();
      if (success) setNotice(success);
      await load();
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'The business request could not be completed.');
    } finally {
      setBusy(false);
    }
  };

  const startCheckout = async (plan: BusinessRecord) => {
    if (!status.checkout_configured) {
      setError('Payment checkout is not configured by the merchant administrator.');
      return;
    }
    setBusy(true);
    setError('');
    setNotice('');
    try {
      const recurring = plan.billing_interval === 'monthly' || plan.billing_interval === 'yearly';
      const checkout = await careerRequest<BusinessRecord>(
        token,
        recurring ? '/business/subscriptions/checkout' : '/business/checkout',
        {
          method: 'POST',
          body: {
            plan_id: plan.id,
            ...(!recurring && couponCode.trim() ? { coupon_code: couponCode.trim() } : {}),
          },
        },
      );
      if (checkout.provider === 'stripe') {
        if (typeof checkout.checkout_url !== 'string') {
          throw new Error('Stripe did not return a secure checkout URL.');
        }
        window.location.assign(checkout.checkout_url);
        return;
      }
      await openRazorpay({
        key: String(checkout.key_id),
        amount: typeof checkout.amount === 'number' ? checkout.amount : undefined,
        currency: typeof checkout.currency === 'string' ? checkout.currency : undefined,
        name: String(checkout.name || 'Career Platform'),
        description: String(checkout.description || plan.name || 'Plan'),
        order_id: typeof checkout.order_id === 'string' ? checkout.order_id : undefined,
        subscription_id: typeof checkout.subscription_id === 'string' ? checkout.subscription_id : undefined,
        theme: { color: '#4f46e5' },
        handler: async (result) => {
          const isSubscription = Boolean(result.razorpay_subscription_id);
          await run(
            () => careerRequest(token, isSubscription ? '/business/subscriptions/verify' : '/business/checkout/verify', {
              method: 'POST',
              body: isSubscription ? {
                razorpay_subscription_id: result.razorpay_subscription_id,
                razorpay_payment_id: result.razorpay_payment_id,
                razorpay_signature: result.razorpay_signature,
              } : {
                razorpay_order_id: result.razorpay_order_id,
                razorpay_payment_id: result.razorpay_payment_id,
                razorpay_signature: result.razorpay_signature,
              },
            }),
            'The payment provider confirmed your payment.',
          );
        },
        modal: { ondismiss: () => setNotice('Checkout was closed; no payment was confirmed.') },
      });
    } catch (requestError) {
      setError(requestError instanceof Error ? requestError.message : 'Checkout could not be started.');
    } finally {
      setBusy(false);
    }
  };

  const submitLead = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void run(() => careerRequest(token, '/business/leads', {
      method: 'POST',
      body: { lead_type: leadType, organization, details: leadDetails },
    }), 'Partnership request submitted.');
  };

  const submitListing = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const price = Number(listingPrice);
    if (!Number.isSafeInteger(price) || price <= 0) {
      setError('Enter a positive price in the smallest currency unit (for example, paise for INR).');
      return;
    }
    void run(() => careerRequest(token, '/business/marketplace/listings', {
      method: 'POST',
      body: {
        listing_type: listingType, title: listingTitle, description: listingDescription,
        price_minor: price, currency: listingCurrency,
      },
    }), 'Marketplace listing submitted for administrator review.');
  };

  const submitAdminPlan = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    let entitlements: BusinessRecord;
    try {
      entitlements = objectValue(JSON.parse(newPlan.entitlements));
    } catch {
      setError('Plan entitlements must be valid JSON.');
      return;
    }
    void run(() => careerRequest(token, '/business/admin/plans', {
      method: 'POST',
      body: {
        ...newPlan,
        price_minor: Number(newPlan.price_minor),
        credits_grant: Number(newPlan.credits_grant),
        entitlements,
      },
    }), 'Plan created and provider plan configured.');
  };

  const submitCoupon = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    void run(() => careerRequest(token, '/business/admin/coupons', {
      method: 'POST',
      body: {
        ...couponForm,
        discount_value: Number(couponForm.discount_value),
        max_redemptions: couponForm.max_redemptions ? Number(couponForm.max_redemptions) : null,
        expires_at: couponForm.expires_at ? new Date(couponForm.expires_at).toISOString() : null,
      },
    }), 'Coupon created.');
  };

  const metrics = objectValue(adminOverview.metrics);
  const activePlan = objectValue(entitlements.plan);
  const features = objectValue(entitlements.features);
  const checkoutProviders = objectValue(status.checkout_providers);
  const webhookProviders = objectValue(status.webhook_providers);
  const canCheckoutForCurrency = (currencyValue: unknown, recurring: boolean): boolean => {
    const currency = typeof currencyValue === 'string' ? currencyValue.toUpperCase() : 'INR';
    const razorpayReady = Boolean(checkoutProviders.razorpay)
      && (!recurring || Boolean(webhookProviders.razorpay));
    const provider = currency === 'INR' && razorpayReady ? 'razorpay' : 'stripe';
    return Boolean(checkoutProviders[provider])
      && (!recurring || Boolean(webhookProviders[provider]));
  };
  const canCheckout = (plan: BusinessRecord): boolean =>
    canCheckoutForCurrency(
      plan.currency,
      plan.billing_interval === 'monthly' || plan.billing_interval === 'yearly',
    );

  return (
    <div className="business-revenue">
      {error && <div className="career-alert career-alert-error" role="alert">{error}</div>}
      {notice && <div className="career-alert career-alert-success" role="status">{notice}</div>}
      {busy && <div className="career-action-progress" role="status">Processing securely…</div>}

      <section className="career-panel business-credit-summary">
        <div>
          <p className="career-eyebrow">ACCOUNT AND USAGE</p>
          <h2>{String(activePlan.name || 'Free plan')}</h2>
          <p className="career-muted">{String(entitlements.status || 'active')}{entitlements.current_period_end ? ` · renews or ends ${formatDate(entitlements.current_period_end)}` : ''}</p>
        </div>
        <div className="business-credit-balance"><Wallet size={19} /><strong>{String(credits.available ?? entitlements.credit_balance ?? 0)}</strong><span>available credits</span></div>
        <div className="career-disclaimer">
          {String(status.billing_note || 'Payments are confirmed by the payment provider.')}
          {!status.checkout_configured && <span> Checkout is unavailable until an authorized merchant configures a payment provider.</span>}
        </div>
      </section>

      <section className="career-panel">
        <div className="career-panel-heading"><div><p className="career-eyebrow">PLANS AND PURCHASES</p><h2>Choose a configured plan</h2></div><CreditCard size={19} /></div>
        {plans.length ? <div className="business-plan-grid">
          {plans.map((plan) => <article className="business-plan-card" key={String(plan.id)}>
            <p className="career-eyebrow">{String(plan.tier).replaceAll('_', ' ')}</p>
            <h3>{String(plan.name)}</h3>
            <strong>{formatMoney(plan.price_minor, plan.currency)}</strong>
            <span>{String(plan.billing_interval).replaceAll('_', ' ')} · {String(plan.credits_grant || 0)} credits included</span>
            <ul>{Object.entries(objectValue(plan.entitlements)).filter(([, enabled]) => Boolean(enabled)).map(([key]) => <li key={key}>{key.replaceAll('_', ' ')}</li>)}</ul>
            <button type="button" className="btn btn-primary" disabled={busy || !canCheckout(plan)} onClick={() => startCheckout(plan)}>
              {plan.billing_interval === 'monthly' || plan.billing_interval === 'yearly' ? 'Subscribe securely' : 'Purchase securely'} <ArrowRight size={15} />
            </button>
          </article>)}
        </div> : <p className="career-muted">No paid prices are configured. The free career workspace remains available; an administrator can publish verified plan prices.</p>}
        <label className="career-field-label business-coupon-field">One-time coupon code<input value={couponCode} onChange={(event) => setCouponCode(event.target.value)} placeholder="Optional; recurring plans require provider plan discounts" /></label>
        <div className="business-feature-list"><strong>Current feature access</strong>{Object.entries(features).map(([key, enabled]) => <span className="career-pill" key={key}>{key.replaceAll('_', ' ')} · {String(enabled)}</span>)}</div>
        {Boolean(activePlan.id && activePlan.id !== 'free') && <>
          {entitlements.provider === 'stripe' ? <p className="career-disclaimer">Stripe plan changes are not enabled yet. You can cancel renewal at period end and choose another plan after the current period.</p> : <>
            <label className="career-field-label">Schedule a plan change<select id="business-plan-change"><option value="">Select an available plan</option>{plans.filter((plan) => plan.billing_interval === 'monthly' || plan.billing_interval === 'yearly').map((plan) => <option key={String(plan.id)} value={String(plan.id)}>{String(plan.name)} · {formatMoney(plan.price_minor, plan.currency)}</option>)}</select></label>
            <button type="button" className="btn btn-secondary" disabled={busy} onClick={() => {
              const selected = document.getElementById('business-plan-change') as HTMLSelectElement | null;
              if (!selected?.value) { setError('Select a subscription plan first.'); return; }
              void run(() => careerRequest(token, `/business/subscriptions/${encodeURIComponent(String(entitlements.subscription_id))}/change`, {
                method: 'POST', body: { plan_id: selected.value },
              }), 'Plan change scheduled with the payment provider.');
            }}>Schedule plan change</button>
          </>}
          <button type="button" className="career-link-button" disabled={busy} onClick={() => {
            if (!window.confirm('Cancel renewal at the end of the current billing period?')) return;
            void run(() => careerRequest(token, `/business/subscriptions/${encodeURIComponent(String(entitlements.subscription_id))}/cancel`, { method: 'POST' }), 'Subscription cancellation scheduled.');
          }}>Cancel renewal at period end</button>
        </>}
      </section>

      <div className="career-two-columns">
        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">SUBSCRIPTION HISTORY</p><h2>Plan lifecycle</h2></div><CreditCard size={18} /></div>
          {subscriptions.length ? subscriptions.map((item) => <article className="career-command-item" key={String(item.id)}><strong>{String(item.plan_name)} · {String(item.status)}</strong><span>{String(item.provider)} · {String(item.billing_interval)} · period {formatDate(item.current_period_start)} – {formatDate(item.current_period_end)}</span>{Boolean(item.cancel_at_period_end) && <small>Renewal is scheduled to cancel at period end.</small>}{Boolean(item.pending_plan_id) && <small>Plan change pending: {String(item.pending_plan_id)}</small>}<small>Started {formatDate(item.created_at)}</small></article>) : <p className="career-muted">No subscription history yet.</p>}
        </section>
        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">CREDIT HISTORY</p><h2>Usage and balance</h2></div><Wallet size={18} /></div>
          <p className="career-disclaimer">Credits are reserved before an eligible AI operation and deducted only after a successful result.</p>
          {arrayValue(credits.transactions).length ? arrayValue(credits.transactions).map((entry, index) => <article className="career-command-item" key={`${String(entry.created_at)}-${index}`}><strong>{String(entry.operation).replaceAll('_', ' ')} · {Number(entry.delta) > 0 ? '+' : ''}{String(entry.delta)} credits</strong><small>{String(entry.entry_type).replaceAll('_', ' ')} · {formatDate(entry.created_at)} · balance {String(entry.balance_after)}</small></article>) : <p className="career-muted">Credit activity appears after credits are granted or eligible AI operations complete.</p>}
        </section>
        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">PAYMENT HISTORY</p><h2>Verified transactions</h2></div><ShieldCheck size={18} /></div>
          {transactions.length ? transactions.map((item) => <article className="career-command-item" key={String(item.id)}><strong>{formatMoney(item.amount_minor, item.currency)} · {String(item.status)}</strong><span>{String(item.provider)} · {String(item.purpose).replaceAll('_', ' ')}{item.discount_minor ? ` · discount ${formatMoney(item.discount_minor, item.currency)}` : ''}</span><small>{formatDate(item.captured_at || item.created_at)}{Number(item.failed_attempts) ? ` · ${String(item.failed_attempts)} failed payment attempt(s)` : ''}</small></article>) : <p className="career-muted">No payment transactions have been recorded.</p>}
        </section>
      </div>

      <div className="career-two-columns">
        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">REFERRALS</p><h2>Invite and earn credits</h2></div><Gift size={18} /></div>
          <p className="career-muted">Your referral code: <strong>{String(referrals.code || '—')}</strong></p>
          <p className="career-disclaimer">{String(referrals.reward_rule || 'Rewards require a verified paid transaction and are configurable by an administrator.')}</p>
          <div className="business-share-row"><input readOnly value={typeof referrals.referral_url === 'string' ? `${window.location.origin}${referrals.referral_url}` : ''} /><button type="button" className="btn btn-secondary" onClick={() => {
            const url = `${window.location.origin}${String(referrals.referral_url || '')}`;
            if (!navigator.clipboard?.writeText) {
              setError('Clipboard access is unavailable in this browser; copy the invite link from the field.');
              return;
            }
            void navigator.clipboard.writeText(url).then(() => setNotice('Referral link copied.')).catch(() => setError('Could not copy the referral link.'));
          }}>Copy invite link</button></div>
          <form className="career-inline-form" onSubmit={(event) => {
            event.preventDefault();
            void run(() => careerRequest(token, '/business/referrals/claim', { method: 'POST', body: { code: claimCode } }), 'Referral code applied to your account.');
          }}><input value={claimCode} onChange={(event) => setClaimCode(event.target.value)} placeholder="Enter a referral code" required /><button className="btn btn-secondary" disabled={busy}>Apply code</button></form>
          {arrayValue(referrals.referrals).map((item, index) => <p className="career-muted" key={`${String(item.created_at)}-${index}`}>{String(item.status)} · {String(item.reward_credits)} credits · {formatDate(item.created_at)}</p>)}
        </section>
        <section className="career-panel">
          <div className="career-panel-heading"><div><p className="career-eyebrow">AFFILIATE PROGRAM</p><h2>Partner commissions</h2></div><BadgePercent size={18} /></div>
          {affiliate.affiliate ? <p className="career-muted">Status: {String(objectValue(affiliate.affiliate).status)} · code {String(objectValue(affiliate.affiliate).code)} · {Number(objectValue(affiliate.affiliate).commission_basis_points) / 100}% commission</p> : <p className="career-muted">Apply to join; commission rates and approval are administered by the platform.</p>}
          <button type="button" className="btn btn-secondary" disabled={busy || Boolean(affiliate.affiliate)} onClick={() => void run(() => careerRequest(token, '/business/affiliates', { method: 'POST', body: { notes: '' } }), 'Affiliate application submitted for review.')}>Apply as affiliate</button>
          {arrayValue(affiliate.conversions).map((item, index) => <article className="career-command-item" key={`${String(item.created_at)}-${index}`}><strong>{String(item.commission_minor)} minor currency units · {String(item.status)}</strong><small>{formatDate(item.created_at)}</small></article>)}
          <p className="career-disclaimer">{String(affiliate.note || 'Commissions are shown as pending until formally approved and reconciled as paid.')}</p>
        </section>
      </div>

      <section className="career-panel">
        <div className="career-panel-heading"><div><p className="career-eyebrow">INSTITUTIONAL PLANS</p><h2>Student, enterprise, recruitment, and university access</h2></div><BriefcaseBusiness size={18} /></div>
        <form className="career-search-form" onSubmit={submitLead}>
          <label><span>Request type</span><select value={leadType} onChange={(event) => setLeadType(event.target.value)}><option value="student">Student pricing</option><option value="enterprise">Enterprise plan</option><option value="recruitment">Recruitment partnership</option><option value="university">University / college partnership</option></select></label>
          <label><span>Organization</span><input required value={organization} onChange={(event) => setOrganization(event.target.value)} /></label>
          <label><span>Details</span><input value={leadDetails} onChange={(event) => setLeadDetails(event.target.value)} /></label>
          <button className="btn btn-primary" disabled={busy}>Submit request</button>
        </form>
        {leads.map((lead) => <article className="career-command-item" key={String(lead.id)}><strong>{String(lead.organization)} · {String(lead.lead_type)}</strong><span>{String(lead.status)} · submitted {formatDate(lead.created_at)}</span></article>)}
      </section>

      <section className="career-panel">
        <div className="career-panel-heading"><div><p className="career-eyebrow">CAREER SERVICES MARKETPLACE</p><h2>Professional services and templates</h2></div><Store size={18} /></div>
        <p className="career-disclaimer">Listings are user-submitted and admin-reviewed. Prices are provider-defined; transactions are verified through the configured payment gateway. Cancellation and disputes are recorded as workflow states, not guaranteed refunds.</p>
        <div className="business-plan-grid">
          {listings.map((item) => <article className="business-plan-card" key={String(item.id)}><p className="career-eyebrow">{String(item.listing_type).replaceAll('_', ' ')}</p><h3>{String(item.title)}</h3><p>{String(item.description)}</p><strong>{formatMoney(item.price_minor, item.currency)}</strong><button className="btn btn-primary" type="button" disabled={busy || !canCheckoutForCurrency(item.currency, false)} onClick={async () => {
            setBusy(true); setError('');
            try {
              const checkout = await careerRequest<BusinessRecord>(token, `/business/marketplace/${encodeURIComponent(String(item.id))}/orders`, {
                method: 'POST', body: { requirements: orderRequirements[String(item.id)] || '' },
              });
              if (checkout.provider === 'stripe') {
                if (typeof checkout.checkout_url !== 'string') {
                  throw new Error('Stripe did not return a secure checkout URL.');
                }
                window.location.assign(checkout.checkout_url);
                return;
              }
              await openRazorpay({
                key: String(checkout.key_id), amount: Number(checkout.amount), currency: String(checkout.currency),
                name: String(checkout.name), description: String(checkout.description),
                order_id: String(checkout.razorpay_order_id), theme: { color: '#4f46e5' },
                handler: async (result) => {
                  if (!result.razorpay_order_id) {
                    setError('The payment callback did not include a provider order reference.');
                    return;
                  }
                  await run(() => careerRequest(token, '/business/checkout/verify', {
                    method: 'POST',
                    body: {
                      razorpay_order_id: result.razorpay_order_id,
                      razorpay_payment_id: result.razorpay_payment_id,
                      razorpay_signature: result.razorpay_signature,
                    },
                  }), 'The payment provider confirmed the marketplace payment.');
                },
              });
            } catch (requestError) {
              setError(requestError instanceof Error ? requestError.message : 'Marketplace checkout could not be started.');
            } finally { setBusy(false); }
          }}>Order securely</button><label className="career-field-label">Requirements<textarea rows={2} value={orderRequirements[String(item.id)] || ''} onChange={(event) => setOrderRequirements((current) => ({ ...current, [String(item.id)]: event.target.value }))} /></label></article>)}
          {!listings.length && <p className="career-muted">No reviewed marketplace listings are currently available.</p>}
        </div>
        <form className="career-form business-listing-form" onSubmit={submitListing}>
          <h3>Submit a service or template listing</h3>
          <label>Category<select value={listingType} onChange={(event) => setListingType(event.target.value)}><option value="resume_review">Resume review</option><option value="career_coaching">Career coaching</option><option value="resume_template">Resume template</option></select></label>
          <label>Title<input required minLength={4} value={listingTitle} onChange={(event) => setListingTitle(event.target.value)} /></label>
          <label>Description<textarea required minLength={20} value={listingDescription} onChange={(event) => setListingDescription(event.target.value)} /></label>
          <div className="career-search-form"><label>Price in minor units<input type="number" min="1" required value={listingPrice} onChange={(event) => setListingPrice(event.target.value)} /></label><label>Currency<input maxLength={3} value={listingCurrency} onChange={(event) => setListingCurrency(event.target.value.toUpperCase())} /></label></div>
          <button className="btn btn-secondary" disabled={busy}>Submit for review</button>
        </form>
        {orders.map((order) => <article className="career-command-item" key={String(order.id)}><strong>{String(order.title)} · {String(order.status)} · {formatMoney(order.amount_minor, order.currency)}</strong><small>{formatDate(order.created_at)}{order.requirements ? ` · ${String(order.requirements)}` : ''}</small>{Boolean(order.is_provider) && ['paid', 'in_progress'].includes(String(order.status)) && <label className="career-field-label">Update fulfillment<select value={String(order.status)} onChange={(event) => {
          const next = event.target.value;
          void run(() => careerRequest(token, `/business/marketplace/orders/${encodeURIComponent(String(order.id))}`, { method: 'PATCH', body: { status: next, note: '' } }), 'Order status updated.');
        }}><option value={String(order.status)}>{String(order.status)}</option><option value="in_progress">In progress</option><option value="completed">Completed</option></select></label>}{Boolean(order.is_customer) && order.status === 'paid' && <div className="business-market-actions"><button type="button" className="career-link-button" disabled={busy} onClick={() => void run(() => careerRequest(token, `/business/marketplace/orders/${encodeURIComponent(String(order.id))}`, { method: 'PATCH', body: { status: 'cancelled', note: '' } }), 'Order cancellation recorded.')}>Cancel before fulfillment</button><button type="button" className="career-link-button" disabled={busy} onClick={() => void run(() => careerRequest(token, `/business/marketplace/orders/${encodeURIComponent(String(order.id))}`, { method: 'PATCH', body: { status: 'disputed', note: '' } }), 'Dispute opened for administrator follow-up.')}>Open dispute</button></div>}</article>)}
      </section>

      {Boolean(status.admin) && <section className="career-panel business-admin-panel">
        <div className="career-panel-heading"><div><p className="career-eyebrow">ROLE-RESTRICTED CONTROLS</p><h2>Business administration</h2></div><ShieldCheck size={18} /></div>
        <p className="career-disclaimer">Admin access is granted only by the backend email allowlist. Revenue is reported only from captured provider transactions.</p>
        <div className="business-metric-grid">
          {Object.entries(metrics).map(([key, value]) => <article key={key}><strong>{Array.isArray(value) ? value.map((row) => `${String(objectValue(row).currency)} ${String(objectValue(row).amount_minor)}`).join(', ') : String(value)}</strong><span>{key.replaceAll('_', ' ')}</span></article>)}
        </div>
        <form className="career-form" onSubmit={submitAdminPlan}>
          <h3>Publish a priced plan</h3>
          <label>Plan identifier<input required pattern="[a-z0-9][a-z0-9_-]*" value={newPlan.id} onChange={(event) => setNewPlan((current) => ({ ...current, id: event.target.value }))} /></label>
          <label>Plan name<input required value={newPlan.name} onChange={(event) => setNewPlan((current) => ({ ...current, name: event.target.value }))} /></label>
          <div className="career-search-form"><label>Tier<select value={newPlan.tier} onChange={(event) => setNewPlan((current) => ({ ...current, tier: event.target.value }))}><option value="starter">Starter</option><option value="pro">Pro</option><option value="premium">Premium</option><option value="student">Student</option><option value="enterprise">Enterprise</option></select></label><label>Billing interval<select value={newPlan.billing_interval} onChange={(event) => setNewPlan((current) => ({ ...current, billing_interval: event.target.value }))}><option value="monthly">Monthly</option><option value="yearly">Yearly</option><option value="one_time">One-time</option></select></label></div>
          <div className="career-search-form"><label>Price in minor units<input type="number" min="1" required value={newPlan.price_minor} onChange={(event) => setNewPlan((current) => ({ ...current, price_minor: event.target.value }))} /></label><label>Currency<input maxLength={3} value={newPlan.currency} onChange={(event) => setNewPlan((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} /></label><label>Credits per period / purchase<input type="number" min="0" value={newPlan.credits_grant} onChange={(event) => setNewPlan((current) => ({ ...current, credits_grant: event.target.value }))} /></label></div>
          <label>Feature entitlements (JSON object)<textarea rows={5} value={newPlan.entitlements} onChange={(event) => setNewPlan((current) => ({ ...current, entitlements: event.target.value }))} /></label>
          <p className="career-disclaimer">Entitlements can be configured through the admin API. Monthly/yearly plans are created at Razorpay using these administrator-supplied prices.</p>
          <button className="btn btn-primary" disabled={busy || !status.checkout_configured}>Create and publish plan</button>
        </form>
        <h3>Published plans</h3>
        {arrayValue(adminOverview.plans).map((plan) => <article className="career-command-item" key={String(plan.id)}><strong>{String(plan.name)} · {String(plan.tier)} · {formatMoney(plan.price_minor, plan.currency)}</strong><small>{String(plan.billing_interval)} · {plan.active ? 'active' : 'inactive'} · {String(plan.credits_grant)} credits</small><button type="button" className="career-link-button" disabled={busy} onClick={() => void run(() => careerRequest(token, `/business/admin/plans/${encodeURIComponent(String(plan.id))}/active?active=${String(!plan.active)}`, { method: 'PATCH' }), `Plan ${plan.active ? 'disabled' : 'activated'}.`)}>{plan.active ? 'Disable plan' : 'Activate plan'}</button></article>)}
        <form className="career-form" onSubmit={submitCoupon}>
          <h3>Configure one-time coupon</h3>
          <label>Code<input required value={couponForm.code} onChange={(event) => setCouponForm((current) => ({ ...current, code: event.target.value }))} /></label>
          <div className="career-search-form"><label>Discount type<select value={couponForm.discount_type} onChange={(event) => setCouponForm((current) => ({ ...current, discount_type: event.target.value }))}><option value="percent">Percent</option><option value="fixed">Fixed</option></select></label><label>Discount value<input type="number" min="1" required value={couponForm.discount_value} onChange={(event) => setCouponForm((current) => ({ ...current, discount_value: event.target.value }))} /></label>{couponForm.discount_type === 'fixed' && <label>Currency<input maxLength={3} value={couponForm.currency} onChange={(event) => setCouponForm((current) => ({ ...current, currency: event.target.value.toUpperCase() }))} /></label>}<label>Maximum redemptions<input type="number" min="1" value={couponForm.max_redemptions} onChange={(event) => setCouponForm((current) => ({ ...current, max_redemptions: event.target.value }))} /></label><label>Expiration (local time)<input type="datetime-local" value={couponForm.expires_at} onChange={(event) => setCouponForm((current) => ({ ...current, expires_at: event.target.value }))} /></label></div>
          <button className="btn btn-secondary" disabled={busy}>Create coupon</button>
        </form>
        <h3>Coupons</h3>
        {adminCoupons.map((coupon) => <article className="career-command-item" key={String(coupon.id)}><strong>{String(coupon.code)} · {coupon.discount_type === 'percent' ? `${String(coupon.discount_value)}%` : formatMoney(coupon.discount_value, coupon.currency)}</strong><small>{String(coupon.redemption_count)} redeemed{coupon.max_redemptions ? ` / ${String(coupon.max_redemptions)}` : ''} · expires {formatDate(coupon.expires_at)}</small><button type="button" className="career-link-button" disabled={busy} onClick={() => void run(() => careerRequest(token, `/business/admin/coupons/${encodeURIComponent(String(coupon.id))}/active?active=${String(!coupon.active)}`, { method: 'PATCH' }), `Coupon ${coupon.active ? 'disabled' : 'activated'}.`)}>{coupon.active ? 'Deactivate coupon' : 'Activate coupon'}</button></article>)}
        <form className="career-form" onSubmit={(event) => {
          event.preventDefault();
          void run(() => careerRequest(token, '/business/admin/settings', {
            method: 'PUT',
            body: {
              free_monthly_credits: Number(adminSettings.free_monthly_credits),
              referral_reward_credits: Number(adminSettings.referral_reward_credits),
            },
          }), 'Business allowances updated.');
        }}>
          <h3>Free allowance and referral reward settings</h3>
          <div className="career-search-form"><label>Free monthly credits<input type="number" min="0" value={String(adminSettings.free_monthly_credits ?? '')} onChange={(event) => setAdminSettings((current) => ({ ...current, free_monthly_credits: event.target.value }))} /></label><label>Referral reward credits<input type="number" min="0" value={String(adminSettings.referral_reward_credits ?? '')} onChange={(event) => setAdminSettings((current) => ({ ...current, referral_reward_credits: event.target.value }))} /></label></div>
          <button className="btn btn-secondary" disabled={busy}>Save credit settings</button>
        </form>
        <h3>AI operation pricing</h3>
        {adminPricing.map((pricing) => <form className="business-pricing-row" key={String(pricing.operation)} onSubmit={(event) => {
          event.preventDefault();
          const form = event.currentTarget;
          const data = new FormData(form);
          void run(() => careerRequest(token, `/business/admin/ai-pricing/${encodeURIComponent(String(pricing.operation))}`, {
            method: 'PUT',
            body: {
              credit_cost: Number(data.get('credit_cost')),
              enabled: data.get('enabled') === 'on',
              required_entitlement: String(data.get('required_entitlement') || '').trim() || null,
            },
          }), `Pricing saved for ${String(pricing.operation)}.`);
        }}><strong>{String(pricing.operation).replaceAll('_', ' ')}</strong><input aria-label="Credit cost" name="credit_cost" type="number" min="1" defaultValue={String(pricing.credit_cost)} /><input aria-label="Required entitlement (optional)" name="required_entitlement" placeholder="No feature gate" defaultValue={String(pricing.required_entitlement || '')} /><label><input name="enabled" type="checkbox" defaultChecked={Boolean(pricing.enabled)} /> Enabled</label><button className="btn btn-secondary" disabled={busy}>Save</button></form>)}
        <h3>Captured transactions and authorized refunds</h3>
        {adminTransactions.map((transaction) => <article className="career-command-item" key={String(transaction.id)}><strong>{formatMoney(transaction.amount_minor, transaction.currency)} · {String(transaction.status)} · {String(transaction.purpose)}</strong><small>{String(transaction.user_email)} · {formatDate(transaction.captured_at || transaction.created_at)}{Number(transaction.failed_attempts) ? ` · ${String(transaction.failed_attempts)} failed attempt(s)` : ''}</small>{transaction.status === 'captured' && transaction.purpose !== 'credits' && Number(transaction.credits_grant || 0) === 0 && <button type="button" className="career-link-button" disabled={busy} onClick={() => {
          const reason = window.prompt('Reason for a full refund (provider-managed):');
          if (!reason) return;
          void run(() => careerRequest(token, `/business/admin/transactions/${encodeURIComponent(String(transaction.id))}/refund`, {
            method: 'POST', body: { reason },
          }), 'Full refund request sent to the payment provider.');
        }}>Request full refund</button>}</article>)}
        <h3>Partnership requests</h3>
        {adminLeads.map((lead) => <article className="career-command-item" key={String(lead.id)}><strong>{String(lead.organization)} · {String(lead.lead_type)} · {String(lead.email)}</strong><span>{String(lead.details)}</span><label className="career-field-label">Request status<select value={String(lead.status)} onChange={(event) => void run(() => careerRequest(token, `/business/admin/leads/${encodeURIComponent(String(lead.id))}`, { method: 'PATCH', body: { status: event.target.value } }), 'Partnership request updated.')}><option value={String(lead.status)}>{String(lead.status)}</option><option value="reviewing">Reviewing</option><option value="approved">Approved</option><option value="declined">Declined</option><option value="closed">Closed</option></select></label></article>)}
        <h3>Affiliate applicants</h3>
        {adminAffiliates.map((item) => <article className="career-command-item" key={String(item.user_id)}><strong>{String(item.email)} · {String(item.status)} · {String(item.code)}</strong><small>Current commission: {Number(item.commission_basis_points) / 100}%</small><button type="button" className="career-link-button" disabled={busy} onClick={() => {
          const basisPoints = window.prompt('Commission in basis points (for example 500 = 5%):', String(item.commission_basis_points));
          if (basisPoints === null) return;
          const value = Number(basisPoints);
          if (!Number.isInteger(value) || value < 0 || value > 10000) { setError('Enter an integer from 0 to 10000 basis points.'); return; }
          void run(() => careerRequest(token, `/business/admin/affiliates/${encodeURIComponent(String(item.user_id))}`, {
            method: 'PATCH', body: { status: value > 0 ? 'approved' : 'rejected', commission_basis_points: value },
          }), 'Affiliate application updated.');
        }}>{item.status === 'approved' ? 'Update commission' : 'Set commission and approve'}</button></article>)}
        <h3>Affiliate commission reconciliation</h3>
        {adminConversions.map((item) => <article className="career-command-item" key={String(item.id)}><strong>{String(item.commission_minor)} minor currency units · {String(item.status)} · {String(item.code)}</strong><small>{formatDate(item.created_at)}</small>{item.status === 'pending' && <div className="business-market-actions"><button type="button" className="career-link-button" disabled={busy} onClick={() => void run(() => careerRequest(token, `/business/admin/affiliate-conversions/${encodeURIComponent(String(item.id))}`, { method: 'PATCH', body: { status: 'approved' } }), 'Commission approved for payment.')}>Approve commission</button><button type="button" className="career-link-button" disabled={busy} onClick={() => void run(() => careerRequest(token, `/business/admin/affiliate-conversions/${encodeURIComponent(String(item.id))}`, { method: 'PATCH', body: { status: 'reversed' } }), 'Commission reversed.')}>Reverse</button></div>}{item.status === 'approved' && <button type="button" className="career-link-button" disabled={busy} onClick={() => void run(() => careerRequest(token, `/business/admin/affiliate-conversions/${encodeURIComponent(String(item.id))}/paid`, { method: 'POST' }), 'Commission marked paid after reconciliation.')}>Mark paid</button>}</article>)}
        <h3>Marketplace listing review</h3>
        {adminListings.map((item) => <article className="career-command-item" key={String(item.id)}><strong>{String(item.title)} · {String(item.listing_type).replaceAll('_', ' ')}</strong><span>{String(item.provider_email)} · {formatMoney(item.price_minor, item.currency)} · {item.active ? 'active' : 'pending review'}</span><p>{String(item.description)}</p>{!item.active && <button type="button" className="career-link-button" disabled={busy} onClick={() => void run(() => careerRequest(token, `/business/admin/marketplace/${encodeURIComponent(String(item.id))}/approve`, { method: 'POST' }), 'Marketplace listing approved.')}>Approve listing</button>}</article>)}
      </section>}
    </div>
  );
};
