package domain

// PageResult is a generic container for paginated query responses.
type PageResult[T any] struct {
	Items      []T
	TotalCount int32
	Limit      int32
	Offset     int32
}

// TotalPages returns the total number of pages given the current page size.
func (p PageResult[T]) TotalPages() int32 {
	if p.Limit <= 0 {
		return 1
	}
	pages := p.TotalCount / p.Limit
	if p.TotalCount%p.Limit != 0 {
		pages++
	}
	if pages == 0 {
		pages = 1
	}
	return pages
}

// CurrentPage returns the 1-based page number derived from offset and limit.
func (p PageResult[T]) CurrentPage() int32 {
	if p.Limit <= 0 {
		return 1
	}
	return (p.Offset / p.Limit) + 1
}

// HasNext reports whether there is a page after the current one.
func (p PageResult[T]) HasNext() bool {
	return p.Offset+p.Limit < p.TotalCount
}

// HasPrev reports whether there is a page before the current one.
func (p PageResult[T]) HasPrev() bool {
	return p.Offset > 0
}
