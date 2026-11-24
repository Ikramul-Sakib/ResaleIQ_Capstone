export const CONDITIONS = [
  { value: 'new', label: 'New' },
  { value: 'like_new', label: 'Like new' },
  { value: 'good', label: 'Good' },
  { value: 'fair', label: 'Fair' },
  { value: 'poor', label: 'Poor' },
]

export const REPORT_REASONS = [
  { value: 'fraud', label: 'Fraud or scam' },
  { value: 'misleading', label: 'Misleading information' },
  { value: 'prohibited', label: 'Prohibited item' },
  { value: 'duplicate', label: 'Duplicate listing' },
  { value: 'offensive', label: 'Offensive content' },
  { value: 'other', label: 'Other' },
]

export const LOCATIONS = [
  'Dhaka', 'Chattogram', 'Sylhet', 'Rajshahi', 'Khulna', 'Barishal', 'Rangpur', 'Mymensingh',
  'Gazipur', 'Narayanganj', 'Cumilla', "Cox's Bazar", 'Bogura', 'Jashore', 'Dinajpur', 'Tangail',
]

export const STATUS_LABELS = {
  pending: 'Pending review',
  approved: 'Live',
  reserved: 'Reserved',
  rejected: 'Rejected',
  sold: 'Sold',
  removed: 'Removed',
}

export const ORDER_STATUS = {
  pending: { label: 'Waiting for seller', css: 'pending' },
  accepted: { label: 'Accepted', css: 'approved' },
  shipped: { label: 'Shipped / handed over', css: 'sold' },
  completed: { label: 'Completed', css: 'approved' },
  declined: { label: 'Declined', css: 'rejected' },
  cancelled: { label: 'Cancelled', css: 'removed' },
}

export const PAYMENT_METHODS = [
  { value: 'cod', label: 'Cash on delivery', hint: 'Pay in cash when you receive the item.' },
  { value: 'bkash', label: 'bKash', hint: "Send money to the seller's bKash number after they accept, then enter the transaction ID." },
  { value: 'nagad', label: 'Nagad', hint: "Send money to the seller's Nagad number after they accept, then enter the transaction ID." },
]

export const DELIVERY_METHODS = [
  { value: 'meetup', label: 'Meet in person', hint: 'Meet the seller at an agreed place.' },
  { value: 'delivery', label: 'Home delivery', hint: 'The seller sends the item to your address (courier cost agreed in chat).' },
]

/** ৳1,25,000 — Bangladeshi digit grouping. */
export function formatPrice(value) {
  if (value === null || value === undefined || value === '') return ''
  return `৳${Number(value).toLocaleString('en-IN')}`
}

export function formatDate(iso) {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' })
}

export function timeAgo(iso) {
  if (!iso) return ''
  const seconds = Math.max(0, (Date.now() - new Date(iso).getTime()) / 1000)
  const steps = [
    [60, 'second'], [60, 'minute'], [24, 'hour'], [7, 'day'], [4.35, 'week'], [12, 'month'], [Infinity, 'year'],
  ]
  let value = seconds
  for (const [size, unit] of steps) {
    if (value < size) {
      const n = Math.floor(value)
      if (unit === 'second') return 'just now'
      return `${n} ${unit}${n === 1 ? '' : 's'} ago`
    }
    value /= size
  }
  return formatDate(iso)
}

/**
 * Shrink a photo in the browser before upload (max 1600 px, JPEG).
 * Phone photos are often 5–10 MB; this keeps uploads fast and under server limits.
 * Falls back to the original file if the browser can't decode it.
 */
export async function compressImage(file, maxSide = 1600, quality = 0.85) {
  if (!file.type.startsWith('image/') || file.size < 400 * 1024) return file
  try {
    const bitmap = await createImageBitmap(file, { imageOrientation: 'from-image' })
    const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height))
    const canvas = document.createElement('canvas')
    canvas.width = Math.round(bitmap.width * scale)
    canvas.height = Math.round(bitmap.height * scale)
    const context = canvas.getContext('2d')
    context.fillStyle = '#fff'
    context.fillRect(0, 0, canvas.width, canvas.height)
    context.drawImage(bitmap, 0, 0, canvas.width, canvas.height)
    bitmap.close?.()
    const blob = await new Promise((resolve) => canvas.toBlob(resolve, 'image/jpeg', quality))
    if (!blob || blob.size >= file.size) return file
    return new File([blob], file.name.replace(/\.\w+$/, '') + '.jpg', { type: 'image/jpeg' })
  } catch {
    return file
  }
}
